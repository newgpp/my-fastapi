from contextlib import asynccontextmanager
import sys

from fastapi import FastAPI
from loguru import logger

from app.api.router import api_router
from app.core.config import get_settings
from app.db.mysql import (
    close_mysql_engine,
    create_mysql_engine,
    create_session_factory,
)
from app.db.redis import close_redis, create_redis


logger.remove()
logger.add(
    sys.stdout,
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss,SSS} {level} {name} {message}",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = await create_redis()
    app.state.mysql_engine = create_mysql_engine()
    app.state.mysql_session_factory = create_session_factory(app.state.mysql_engine)
    try:
        yield
    finally:
        await close_redis(app.state.redis)
        await close_mysql_engine(app.state.mysql_engine)


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=9090,
        reload=True,
    )

