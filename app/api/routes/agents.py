from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.services import agent_service
from loguru import logger

router = APIRouter(prefix="/agents", tags=["agents"])


async def _stream_with_disconnect(request: Request, generator):
    """断线检测+资源清理"""
    """break作用 切断“上游 generator → 下游消费者”的数据拉动链"""
    """要不要手动清理 generator，取决于 generator 是不是“持有资源”的异步生成器"""
    normal_end = False
    try:
        async for chunk in generator:
            if await request.is_disconnected():
                logger.warning(f"{request.client.host} disconnected")
                break
            yield chunk
        else:
            normal_end = True
    finally:
        try:
            aclose = getattr(generator, "aclose", None)
            if aclose:
                await aclose()
        finally:
            if normal_end:
                logger.info(f"{request.client.host} completed")
            else:
                logger.warning(f"{request.client.host} aborted")


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
