from redis.asyncio import Redis
from redis.asyncio import from_url

from app.core.config import get_settings


async def create_redis() -> Redis:
    settings = get_settings()
    return from_url(
        settings.redis_url,
        password=settings.redis_password,
        decode_responses=True,
        max_connections=50,
        health_check_interval=30,
    )


async def close_redis(client: Redis | None) -> None:
    if client is None:
        return
    await client.close()


async def ping_redis(client: Redis) -> str:
    pong = await client.ping()
    return "PONG" if pong else "NO_PONG"
