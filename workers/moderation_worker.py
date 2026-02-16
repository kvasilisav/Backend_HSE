import asyncio
import json
import logging
import os
import sys
from typing import Optional

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clients.kafka import KafkaProducer, DLQ_TOPIC, MODERATION_TOPIC
from db.connection import DATABASE_URL, create_pool
from model import get_model
from repositories.ads import AdsRepository
from repositories.moderation_results import ModerationResultsRepository
from services.predict_service import run_prediction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
MAX_RETRIES = 3
RETRY_DELAYS = [1, 5, 30]


async def process_message(
    message_data: dict,
    model,
    pool,
    kafka_producer: KafkaProducer,
    retry_count: int = 0,
):
    item_id = message_data.get("item_id")
    task_id = None

    try:
        ads_repo = AdsRepository(pool)
        results_repo = ModerationResultsRepository(pool)

        result = await pool.fetchrow(
            """
            SELECT id FROM moderation_results
            WHERE item_id = $1 AND status = 'pending'
            ORDER BY created_at ASC LIMIT 1
            """
        )
        if not result:
            logger.warning("No pending task found for item_id=%s", item_id)
            return
        task_id = result["id"]

        ad = await ads_repo.get_by_id(item_id)
        if ad is None:
            error_msg = f"Ad with item_id={item_id} not found"
            logger.error(error_msg)
            await results_repo.update_failed(task_id, error_msg)
            await kafka_producer.send_to_dlq(message_data, error_msg, retry_count)
            return

        is_violation, probability = run_prediction(
            model=model,
            seller_id=ad["seller_id"],
            is_verified_seller=ad["is_verified_seller"],
            item_id=ad["id"],
            description=ad["description"],
            category=ad["category"],
            images_qty=ad["images_qty"],
        )

        await results_repo.update_completed(task_id, is_violation, probability)
        logger.info(
            "Processed moderation for item_id=%s, task_id=%s, violation=%s",
            item_id,
            task_id,
            is_violation,
        )

    except Exception as exc:
        error_msg = str(exc)
        logger.exception("Error processing message: %s", error_msg)

        if retry_count < MAX_RETRIES:
            delay = RETRY_DELAYS[min(retry_count, len(RETRY_DELAYS) - 1)]
            logger.info(
                "Retrying in %s seconds (attempt %s/%s)",
                delay,
                retry_count + 1,
                MAX_RETRIES,
            )
            await asyncio.sleep(delay)
            await process_message(
                message_data, model, pool, kafka_producer, retry_count + 1
            )
        else:
            logger.error("Max retries reached, sending to DLQ")
            if task_id:
                results_repo = ModerationResultsRepository(pool)
                await results_repo.update_failed(task_id, error_msg)
            await kafka_producer.send_to_dlq(message_data, error_msg, retry_count)


async def main():
    logger.info("Starting moderation worker")

    model = get_model()
    if model is None:
        logger.error("Model not loaded, exiting")
        sys.exit(1)

    pool = await create_pool()
    kafka_producer = KafkaProducer(KAFKA_BOOTSTRAP_SERVERS)
    await kafka_producer.start()

    consumer = AIOKafkaConsumer(
        MODERATION_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="moderation_workers",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        enable_auto_commit=True,
    )

    try:
        await consumer.start()
        logger.info("Consumer started, waiting for messages...")

        async for message in consumer:
            try:
                message_data = message.value
                logger.info("Received message: %s", message_data)
                await process_message(message_data, model, pool, kafka_producer)
            except Exception as exc:
                logger.exception("Error handling message: %s", exc)

    except KafkaError as exc:
        logger.error("Kafka error: %s", exc)
    finally:
        await consumer.stop()
        await kafka_producer.stop()
        await pool.close()
        logger.info("Worker stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as exc:
        logger.exception("Fatal error: %s", exc)
        sys.exit(1)
