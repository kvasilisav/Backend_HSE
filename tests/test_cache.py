import pytest
from unittest.mock import AsyncMock, MagicMock

from storages.cache import (
    PredictionCache,
    cache_key_moderation_result,
    cache_key_predict,
    cache_key_simple_predict,
)


@pytest.fixture
def mock_redis():
    r = MagicMock()
    r.get = AsyncMock(return_value=None)
    r.set = AsyncMock(return_value=True)
    r.delete = AsyncMock(return_value=1)
    return r


def test_cache_key_predict():
    key = cache_key_predict(1, True, 2, 100, 5, 3)
    assert key == "predict:1:1:2:100:5:3"


def test_cache_key_simple_predict():
    assert cache_key_simple_predict(42) == "simple_predict:42"


def test_cache_key_moderation_result():
    assert cache_key_moderation_result(10) == "moderation_result:10"


@pytest.mark.asyncio
async def test_cache_get_miss(mock_redis):
    cache = PredictionCache(mock_redis)
    mock_redis.get.return_value = None
    result = await cache.get("key1")
    assert result is None
    mock_redis.get.assert_called_once_with("key1")


@pytest.mark.asyncio
async def test_cache_get_hit(mock_redis):
    cache = PredictionCache(mock_redis)
    mock_redis.get.return_value = '{"is_violation": true, "probability": 0.9}'
    result = await cache.get("key1")
    assert result == {"is_violation": True, "probability": 0.9}
    mock_redis.get.assert_called_once_with("key1")


@pytest.mark.asyncio
async def test_cache_set_calls_redis_with_ttl(mock_redis):
    cache = PredictionCache(mock_redis)
    await cache.set("key1", {"is_violation": False, "probability": 0.1})
    mock_redis.set.assert_called_once()
    args, kwargs = mock_redis.set.call_args
    assert args[0] == "key1"
    assert "is_violation" in args[1]
    assert kwargs.get("ex") == 3600


@pytest.mark.asyncio
async def test_cache_delete(mock_redis):
    cache = PredictionCache(mock_redis)
    await cache.delete("key1")
    mock_redis.delete.assert_called_once_with("key1")


@pytest.mark.asyncio
async def test_cache_delete_many(mock_redis):
    cache = PredictionCache(mock_redis)
    await cache.delete_many(["a", "b"])
    mock_redis.delete.assert_called_once_with("a", "b")


@pytest.mark.asyncio
async def test_cache_delete_many_empty(mock_redis):
    cache = PredictionCache(mock_redis)
    await cache.delete_many([])
    mock_redis.delete.assert_not_called()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_integration_set_get():
    import os
    import redis.asyncio as redis
    from redis.exceptions import ConnectionError as RedisConnectionError
    from storages.cache import REDIS_URL

    url = os.environ.get("REDIS_URL", REDIS_URL)
    client = redis.from_url(url, decode_responses=True)
    try:
        cache = PredictionCache(client)
        key = "test:integration:1"
        value = {"is_violation": True, "probability": 0.77}
        await cache.set(key, value, ttl=10)
        result = await cache.get(key)
        assert result == value
        await cache.delete(key)
    except RedisConnectionError:
        pytest.skip("Redis not available")
    finally:
        await client.aclose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_integration_get_miss():
    import os
    import redis.asyncio as redis
    from redis.exceptions import ConnectionError as RedisConnectionError
    from storages.cache import REDIS_URL

    url = os.environ.get("REDIS_URL", REDIS_URL)
    client = redis.from_url(url, decode_responses=True)
    try:
        cache = PredictionCache(client)
        result = await cache.get("test:nonexistent:key")
        assert result is None
    except RedisConnectionError:
        pytest.skip("Redis not available")
    finally:
        await client.aclose()
