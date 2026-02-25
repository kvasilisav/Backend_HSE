import json
import logging
from datetime import datetime
from typing import Optional

from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
MODERATION_TOPIC = "moderation"
DLQ_TOPIC = "moderation_dlq"


class KafkaProducer:
    def __init__(self, bootstrap_servers: str = KAFKA_BOOTSTRAP_SERVERS):
        self.bootstrap_servers = bootstrap_servers
        self._producer: Optional[AIOKafkaProducer] = None

    async def start(self):
        if self._producer is None:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            await self._producer.start()
            logger.info("Kafka producer started")

    async def stop(self):
        if self._producer:
            await self._producer.stop()
            self._producer = None
            logger.info("Kafka producer stopped")

    async def send_moderation_request(self, item_id: int, task_id: int):
        await self.start()
        message = {
            "item_id": item_id,
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        await self._producer.send_and_wait(MODERATION_TOPIC, message)
        logger.info("Sent moderation request for item_id=%s task_id=%s", item_id, task_id)

    async def send_to_dlq(
        self, original_message: dict, error: str, retry_count: int = 0
    ):
        await self.start()
        dlq_message = {
            "original_message": original_message,
            "error": error,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "retry_count": retry_count,
        }
        await self._producer.send_and_wait(DLQ_TOPIC, dlq_message)
        logger.warning("Sent message to DLQ: %s", error)
