from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession


async def get_mysql_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    session_factory = request.app.state.mysql_session_factory
    async with session_factory() as session:
        yield session
