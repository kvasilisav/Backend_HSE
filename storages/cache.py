import json
import os

import redis.asyncio as redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
# TTL 1 hour: balance between reducing DB/model load and freshness of moderation results
CACHE_TTL_SECONDS = 3600


class PredictionCache:
    def __init__(self, client: redis.Redis):
        self._client = client
        self._ttl = CACHE_TTL_SECONDS

    async def get(self, key: str):
        data = await self._client.get(key)
        if data is None:
            return None
        return json.loads(data)

    async def set(self, key: str, value: dict, ttl: int | None = None):
        await self._client.set(
            key,
            json.dumps(value),
            ex=ttl if ttl is not None else self._ttl,
        )

    async def delete(self, key: str):
        await self._client.delete(key)

    async def delete_many(self, keys: list[str]):
        if keys:
            await self._client.delete(*keys)


def cache_key_predict(seller_id: int, is_verified: bool, item_id: int, desc_len: int, category: int, images_qty: int) -> str:
    return f"predict:{seller_id}:{int(is_verified)}:{item_id}:{desc_len}:{category}:{images_qty}"


def cache_key_simple_predict(item_id: int) -> str:
    return f"simple_predict:{item_id}"


def cache_key_moderation_result(task_id: int) -> str:
    return f"moderation_result:{task_id}"
