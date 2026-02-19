import asyncio
import contextvars
import json
import time
import uuid
from collections import defaultdict
from typing import Any, AsyncGenerator, Callable

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/memory", tags=["memory"])


class EphemeralContext(BaseModel):
    trace_id: str
    steps: list[str] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    token_usage: dict[str, int] = Field(default_factory=lambda: {"input": 0, "output": 0})


class ProgressEvent(BaseModel):
    trace_id: str
    seq: int
    stage: str
    progress: int
    message: str
    ts: float
    done: bool = False
    error: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


agent_ctx_var: contextvars.ContextVar[EphemeralContext] = contextvars.ContextVar("agent_ctx")


def sse_pack(event: str, data: dict[str, Any], event_id: int | None = None) -> str:
    lines: list[str] = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    lines.append(f"data: {json.dumps(data, ensure_ascii=False)}")
    return "\n".join(lines) + "\n\n"


class ProgressBus:
    def __init__(self) -> None:
        self._subs: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)
        self._seq: dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    async def publish(self, trace_id: str, payload: dict[str, Any]) -> None:
        async with self._lock:
            self._seq[trace_id] += 1
            seq = self._seq[trace_id]
            subscribers = list(self._subs.get(trace_id, set()))

        event = ProgressEvent(trace_id=trace_id, seq=seq, **payload).model_dump()

        for queue in subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                _ = queue.get_nowait()
                queue.put_nowait(event)

    async def cleanup_trace(self, trace_id: str) -> None:
        """Release sequence state when the trace has no active subscribers."""
        async with self._lock:
            subscribers = self._subs.get(trace_id)
            if subscribers:
                return
            self._subs.pop(trace_id, None)
            self._seq.pop(trace_id, None)

    async def subscribe(self, trace_id: str) -> AsyncGenerator[dict[str, Any], None]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=200)
        async with self._lock:
            self._subs[trace_id].add(queue)

        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield {"event": "ping", "trace_id": trace_id, "ts": time.time()}
                    continue

                yield event
                if event.get("done") or event.get("error"):
                    break
        finally:
            async with self._lock:
                subscribers = self._subs.get(trace_id)
                if subscribers is not None:
                    subscribers.discard(queue)
                    if not subscribers:
                        self._subs.pop(trace_id, None)
                        self._seq.pop(trace_id, None)


progress_bus = ProgressBus()


async def emit_progress(
    stage: str,
    progress: int,
    message: str,
    *,
    done: bool = False,
    error: str | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    ctx = agent_ctx_var.get()
    await progress_bus.publish(
        ctx.trace_id,
        {
            "stage": stage,
            "progress": progress,
            "message": message,
            "ts": time.time(),
            "done": done,
            "error": error,
            "meta": meta or {},
        },
    )


async def call_llm_tool(tool_name: str, progress_start: int, progress_end: int) -> None:
    ctx = agent_ctx_var.get()

    ctx.steps.append(f"启动工具: {tool_name}")
    ctx.tool_calls.append({"name": tool_name, "start": time.time()})
    await emit_progress("tool_start", progress_start, f"{tool_name} started", meta={"tool": tool_name})

    await asyncio.sleep(3)

    ctx.token_usage["input"] += 50
    ctx.steps.append(f"{tool_name} 执行完毕")
    await emit_progress("tool_done", progress_end, f"{tool_name} finished", meta={"tool": tool_name})


async def agent_reasoning_logic() -> AsyncGenerator[str, None]:
    ctx = agent_ctx_var.get()
    ctx.steps.append("开始思考用户意图")
    await emit_progress("reasoning", 10, "start reasoning")

    await call_llm_tool("PDF_Parser", progress_start=25, progress_end=55)
    await call_llm_tool("Web_Search", progress_start=60, progress_end=90)

    ctx.token_usage["output"] += 30
    await emit_progress("generate", 95, "generating final answer")
    yield "这是 Agent 最终生成的回答内容。"


async def context_wrapper(
    request: Request, generator_func: Callable[[], AsyncGenerator[str, None]]
) -> AsyncGenerator[str, None]:
    trace_id = request.headers.get("X-Trace-Id", f"tr-{uuid.uuid4().hex[:8]}")
    ctx = EphemeralContext(trace_id=trace_id)
    token = agent_ctx_var.set(ctx)

    try:
        await emit_progress("accepted", 0, "request accepted")
        yield sse_pack("meta", {"trace_id": trace_id})

        async for chunk in generator_func():
            yield sse_pack("answer", {"trace_id": trace_id, "chunk": chunk})

        await emit_progress("done", 100, "completed", done=True, meta={"token": ctx.token_usage})
        yield sse_pack("done", {"trace_id": trace_id, "token": ctx.token_usage})

    except asyncio.CancelledError:
        await emit_progress("cancelled", 100, "client disconnected", error="cancelled")
        raise
    except Exception as exc:
        await emit_progress("failed", 100, "request failed", error=str(exc))
        yield sse_pack("error", {"trace_id": trace_id, "error": str(exc)})
        raise
    finally:
        print(f"统计：Trace={ctx.trace_id}, 总计步骤={len(ctx.steps)}, Token={ctx.token_usage}")
        await progress_bus.cleanup_trace(trace_id)
        agent_ctx_var.reset(token)


@router.get("/chat")
async def chat(request: Request) -> StreamingResponse:
    return StreamingResponse(
        context_wrapper(request, agent_reasoning_logic),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/progress/{trace_id}")
async def progress(trace_id: str) -> StreamingResponse:
    async def stream_progress() -> AsyncGenerator[str, None]:
        async for event in progress_bus.subscribe(trace_id):
            if event.get("event") == "ping":
                yield sse_pack("ping", event)
                continue

            name = "error" if event.get("error") else ("done" if event.get("done") else "progress")
            yield sse_pack(name, event, event_id=event["seq"])

    return StreamingResponse(
        stream_progress(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
