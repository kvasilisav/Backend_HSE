import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from repositories.ads import AdsRepository
from services.predict_service import run_prediction

logger = logging.getLogger(__name__)
router = APIRouter()


class SimplePredictRequest(BaseModel):
    item_id: int = Field(..., gt=0)


class PredictRequest(BaseModel):
    seller_id: int = Field(..., gt=0)
    is_verified_seller: bool
    item_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    category: int = Field(..., gt=0)
    images_qty: int = Field(..., ge=0)


def get_model(request: Request):
    model = getattr(request.app.state, "model", None)
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return model


def get_pool(request: Request):
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="Database not available")
    return pool


@router.post("/predict")
def predict(payload: PredictRequest, model=Depends(get_model)):
    try:
        is_violation, probability = run_prediction(
            model=model,
            seller_id=payload.seller_id,
            is_verified_seller=payload.is_verified_seller,
            item_id=payload.item_id,
            description=payload.description,
            category=payload.category,
            images_qty=payload.images_qty,
        )
        return {"is_violation": is_violation, "probability": probability}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/simple_predict")
async def simple_predict(
    payload: SimplePredictRequest,
    model=Depends(get_model),
    pool=Depends(get_pool),
):
    ads_repo = AdsRepository(pool)
    row = await ads_repo.get_by_id(payload.item_id)
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
