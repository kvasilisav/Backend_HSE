from fastapi import HTTPException

from repositories.ads import AdsRepository
from repositories.moderation_results import ModerationResultsRepository
from storages.cache import PredictionCache, cache_key_moderation_result, cache_key_simple_predict


async def close_ad(item_id: int, pool, cache: PredictionCache | None) -> None:
    ads_repo = AdsRepository(pool)
    results_repo = ModerationResultsRepository(pool)
    task_ids = await results_repo.get_task_ids_by_item_id(item_id)
    await results_repo.delete_by_item_id(item_id)
    closed = await ads_repo.close(item_id)
    if not closed:
        raise HTTPException(status_code=404, detail="Ad not found or already closed")
    if cache:
        keys = [cache_key_simple_predict(item_id)]
        keys.extend(cache_key_moderation_result(tid) for tid in task_ids)
        try:
            await cache.delete_many(keys)
        except Exception:
            pass
