import logging

from fastapi import HTTPException

from clients.kafka import KafkaProducer
from repositories.ads import AdsRepository
from repositories.moderation_results import ModerationResultsRepository

logger = logging.getLogger(__name__)


async def create_moderation_task(item_id: int, pool, kafka_producer: KafkaProducer) -> int:
    ads_repo = AdsRepository(pool)
    ad = await ads_repo.get_by_id(item_id)
    if ad is None:
        raise HTTPException(status_code=404, detail="Ad not found")

    results_repo = ModerationResultsRepository(pool)
    task_id = await results_repo.create(item_id)
    await kafka_producer.send_moderation_request(item_id, task_id)
    return task_id
