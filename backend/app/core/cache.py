"""Redis-backed cache helpers. Falls back to no-op if Redis is unavailable."""

import json
from typing import Any

import redis.asyncio as aioredis

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis | None:
    global _client
    if _client is not None:
        return _client
    try:
        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        await client.ping()
        _client = client
        return _client
    except Exception as exc:
        logger.warning("redis_unavailable", err=str(exc))
        return None


async def cache_get(key: str) -> Any | None:
    client = await get_redis()
    if not client:
        return None
    raw = await client.get(key)
    return json.loads(raw) if raw else None


async def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    client = await get_redis()
    if not client:
        return
    await client.set(key, json.dumps(value, default=str), ex=ttl or settings.cache_ttl_seconds)
