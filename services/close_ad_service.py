from exceptions import AdNotFoundError
from repositories.ads import AdsRepository
from repositories.moderation_results import ModerationResultsRepository
from storages.cache import PredictionCache, cache_key_moderation_result, cache_key_simple_predict


async def close_ad(item_id: int, pool, cache: PredictionCache | None) -> None:
    ads_repo = AdsRepository(pool)
    results_repo = ModerationResultsRepository(pool)
    async with pool.acquire() as conn:
        async with conn.transaction():
            closed = await ads_repo.close(item_id, conn=conn)
            if not closed:
                raise AdNotFoundError("Ad not found or already closed")
            task_ids = await results_repo.get_task_ids_by_item_id(item_id, conn=conn)
            await results_repo.delete_by_item_id(item_id, conn=conn)
    if cache:
        keys = [cache_key_simple_predict(item_id)]
        keys.extend(cache_key_moderation_result(tid) for tid in task_ids)
        try:
            await cache.delete_many(keys)
        except Exception:
            pass
