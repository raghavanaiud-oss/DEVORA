import json
from typing import Any, Optional
import redis.asyncio as aioredis
from backend.app.core.config import settings

redis_pool: Optional[aioredis.ConnectionPool] = None


def get_redis_pool() -> aioredis.ConnectionPool:
    global redis_pool
    if redis_pool is None:
        redis_pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=50,
        )
    return redis_pool


async def get_redis_client() -> aioredis.Redis:
    pool = get_redis_pool()
    return aioredis.Redis(connection_pool=pool)


class RedisPubSubManager:
    """Manages Redis Pub/Sub channels for real-time collaboration rooms."""

    def __init__(self):
        self._client: Optional[aioredis.Redis] = None

    async def get_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = await get_redis_client()
        return self._client

    async def publish_message(self, channel: str, message: Any) -> int:
        client = await self.get_client()
        serialized = json.dumps(message) if not isinstance(message, str) else message
        return await client.publish(channel, serialized)

    async def subscribe(self, channel: str):
        client = await self.get_client()
        pubsub = client.pubsub()
        await pubsub.subscribe(channel)
        return pubsub


pubsub_manager = RedisPubSubManager()
