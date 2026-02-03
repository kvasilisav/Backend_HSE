import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from services.predict_service import run_prediction

logger = logging.getLogger(__name__)

router = APIRouter()


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
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {exc!s}",
        ) from exc
