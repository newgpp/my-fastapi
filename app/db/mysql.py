from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings


def _mysql_dsn() -> str:
    settings = get_settings()
    return (
        "mysql+asyncmy://"
        f"{settings.mysql_user}:{settings.mysql_password}"
        f"@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_db}"
    )


def create_mysql_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        _mysql_dsn(),
        echo=settings.mysql_echo,
        pool_size=5,
        max_overflow=5,
        pool_recycle=1800,
    )


def create_session_factory(engine: AsyncEngine) -> sessionmaker[AsyncSession]:
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def close_mysql_engine(engine: AsyncEngine | None) -> None:
    if engine is None:
        return
    await engine.dispose()


async def mysql_ping(session: AsyncSession) -> list[dict[str, Any]]:
    result = await session.execute(text("SELECT 1 AS ok"))
    return [dict(row) for row in result.mappings().all()]
