from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI()


class PredictRequest(BaseModel):
    seller_id: int = Field(..., gt=0)
    is_verified_seller: bool
    item_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    category: int = Field(..., gt=0)
    images_qty: int = Field(..., ge=0)


def predict_decision(payload: PredictRequest) -> bool:
    if payload.is_verified_seller:
        return True
    return payload.images_qty > 0


@app.post("/predict", response_model=bool)
def predict(payload: PredictRequest) -> bool:
    try:
        return predict_decision(payload)
    except Exception as exc: 
        raise HTTPException(status_code=500, detail="Prediction failed") from exc
