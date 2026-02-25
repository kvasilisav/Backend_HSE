import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from services.close_ad_service import close_ad
from services.predict_service import run_prediction
from services.simple_predict_service import simple_predict
from storages.cache import PredictionCache, cache_key_predict, cache_key_simple_predict

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


def get_cache(request: Request) -> PredictionCache | None:
    return getattr(request.app.state, "cache", None)


@router.post("/predict")
async def predict(
    payload: PredictRequest,
    model=Depends(get_model),
    cache=Depends(get_cache),
):
    key = cache_key_predict(
        payload.seller_id,
        payload.is_verified_seller,
        payload.item_id,
        len(payload.description),
        payload.category,
        payload.images_qty,
    )
    if cache:
        try:
            cached = await cache.get(key)
            if cached is not None:
                return cached
        except Exception:
            pass
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
        result = {"is_violation": is_violation, "probability": probability}
        if cache:
            try:
                await cache.set(key, result)
            except Exception:
                pass
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/simple_predict")
async def simple_predict_handler(
    payload: SimplePredictRequest,
    model=Depends(get_model),
    pool=Depends(get_pool),
    cache=Depends(get_cache),
):
    return await simple_predict(payload.item_id, model, pool, cache)


class CloseAdRequest(BaseModel):
    item_id: int = Field(..., gt=0)


@router.post("/close")
async def close_ad_handler(
    payload: CloseAdRequest,
    pool=Depends(get_pool),
    cache=Depends(get_cache),
):
    await close_ad(payload.item_id, pool, cache)
    return {"message": "Ad closed"}
