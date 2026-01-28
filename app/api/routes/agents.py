from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.services import agent_service

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/llm")
async def llm(request: Request):
    generator = agent_service.llm_stream(request.app.state.llm_sem)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/http")
async def http(request: Request):
    generator = agent_service.echo_http(request.app.state.http_sem)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
