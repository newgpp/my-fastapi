from fastapi import APIRouter

from app.api.routes import demo, users


api_router = APIRouter()
api_router.include_router(demo.router)
api_router.include_router(users.router)
