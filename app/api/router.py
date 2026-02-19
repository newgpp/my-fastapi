from fastapi import APIRouter

from app.api.routes import agents, demo, users, memory


api_router = APIRouter()
api_router.include_router(demo.router)
api_router.include_router(users.router)
api_router.include_router(agents.router)
api_router.include_router(memory.router)
