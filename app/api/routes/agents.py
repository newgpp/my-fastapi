import asyncio
from asyncio import CancelledError
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.services import agent_service
from loguru import logger

router = APIRouter(prefix="/agents", tags=["agents"])


async def _stream_with_disconnect(request: Request, generator):
    """安全的 streaming 包装器：
    - 依赖 ASGI 的取消机制停止流
    - 只做资源清理，不做生命周期控制
    """

    client = getattr(request.client, "host", "unknown")
    normal_end = False

    try:
        async for chunk in generator:
            # 仅用于日志提示，不再控制流程
            yield chunk

        normal_end = True

    except CancelledError:
        # 关键：客户端断开时会走这里
        logger.warning(f"{client} disconnected (cancelled)")
        raise  # 必须继续向上抛，让 ASGI 停止整个调用链

    finally:
        # 只负责关闭上游资源，不阻断取消
        aclose = getattr(generator, "aclose", None)
        if aclose:
            try:
                # 使用 shield 确保即使外层取消了，close 逻辑也能跑完
                await asyncio.wait_for(asyncio.shield(aclose()), timeout=5.0)
            except Exception:
                logger.exception("generator close failed")

        if normal_end:
            logger.info(f"{client} completed")
        else:
            logger.warning(f"{client} aborted")


@router.get("/llm")
async def llm(request: Request):
    generator = agent_service.llm_stream(request.app.state.llm_sem)
    return StreamingResponse(
        _stream_with_disconnect(request, generator),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/http")
async def http(request: Request):
    generator = agent_service.echo_http(request.app.state.http_sem)
    return StreamingResponse(
        _stream_with_disconnect(request, generator),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
