import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from clients.kafka import KafkaProducer, KAFKA_BOOTSTRAP_SERVERS
from repositories.moderation_results import ModerationResultsRepository
from services.async_predict_service import create_moderation_task
from storages.cache import PredictionCache, cache_key_moderation_result

logger = logging.getLogger(__name__)
router = APIRouter()


class AsyncPredictRequest(BaseModel):
    item_id: int = Field(..., gt=0)


def get_pool(request: Request):
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="Database not available")
    return pool


def get_cache(request: Request) -> PredictionCache | None:
    return getattr(request.app.state, "cache", None)


def get_kafka_producer(request: Request) -> KafkaProducer:
    if not hasattr(request.app.state, "kafka_producer"):
        request.app.state.kafka_producer = KafkaProducer(KAFKA_BOOTSTRAP_SERVERS)
    return request.app.state.kafka_producer


@router.post("/async_predict")
async def async_predict(
    payload: AsyncPredictRequest,
    pool=Depends(get_pool),
    kafka_producer=Depends(get_kafka_producer),
):
    try:
        task_id = await create_moderation_task(
            payload.item_id, pool, kafka_producer
        )
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "Moderation request accepted",
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to create moderation task")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/moderation_result/{task_id}")
async def get_moderation_result(
    task_id: int,
    pool=Depends(get_pool),
    cache=Depends(get_cache),
):
    if cache:
        try:
            cached = await cache.get(cache_key_moderation_result(task_id))
            if cached is not None:
                return cached
        except Exception:
            pass
    results_repo = ModerationResultsRepository(pool)
    result = await results_repo.get_by_id(task_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Task not found")
    response = {
        "task_id": result["id"],
        "status": result["status"],
        "is_violation": result["is_violation"],
        "probability": float(result["probability"]) if result["probability"] is not None else None,
        "error_message": result["error_message"],
    }
    if result["status"] in ("completed", "failed") and cache:
        try:
            await cache.set(cache_key_moderation_result(task_id), response)
        except Exception:
            pass
    return response
