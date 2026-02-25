import logging
from typing import TYPE_CHECKING

from fastapi import HTTPException

from repositories.ads import AdsRepository
from services.predict_service import run_prediction
from storages.cache import cache_key_simple_predict

if TYPE_CHECKING:
    from storages.cache import PredictionCache

logger = logging.getLogger(__name__)


async def simple_predict(item_id: int, model, pool, cache: "PredictionCache | None" = None):
    if cache:
        try:
            cached = await cache.get(cache_key_simple_predict(item_id))
            if cached is not None:
                return cached
        except Exception:
            pass
    ads_repo = AdsRepository(pool)
    row = await ads_repo.get_by_id(item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Ad not found")
    try:
        is_violation, probability = run_prediction(
            model=model,
            seller_id=row["seller_id"],
            is_verified_seller=row["is_verified_seller"],
            item_id=row["id"],
            description=row["description"],
            category=row["category"],
            images_qty=row["images_qty"],
        )
        result = {"is_violation": is_violation, "probability": probability}
        if cache:
            try:
                await cache.set(cache_key_simple_predict(item_id), result)
            except Exception:
                pass
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Simple predict failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
