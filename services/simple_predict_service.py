import logging

from fastapi import HTTPException

from repositories.ads import AdsRepository
from services.predict_service import run_prediction

logger = logging.getLogger(__name__)


async def simple_predict(item_id: int, model, pool):
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
        return {"is_violation": is_violation, "probability": probability}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Simple predict failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
