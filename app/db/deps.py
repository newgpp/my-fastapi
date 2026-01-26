from collections.abc import AsyncGenerator
import json
from typing import Any

from fastapi import Depends, HTTPException, Request, Security
from fastapi.logger import logger
from fastapi.security import APIKeyHeader
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession


async def get_mysql_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    session_factory = request.app.state.mysql_session_factory
    async with session_factory() as session:
        yield session


def get_redis(request: Request) -> Redis:
    return request.app.state.redis


api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


async def get_current_user_from_token(
    token: str | None = Security(api_key_header),
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    if token is None:
        raise HTTPException(status_code=401, detail="未登录或令牌无效")
    token = token.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    logger.info("auth token: %s", token)

    if not token:
        raise HTTPException(status_code=401, detail="未登录或令牌无效")

    user_json = await redis.get(f"login:token:{token}")
    if user_json is None:
        raise HTTPException(status_code=401, detail="未登录或令牌无效")

    try:
        return json.loads(user_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=401, detail="未登录或令牌无效") from exc
