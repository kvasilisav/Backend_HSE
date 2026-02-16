import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from db.connection import create_pool
from model import get_model
from routes.async_predict import router as async_predict_router
from routes.predict import router as predict_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.model = get_model()
        logger.info("Model loaded successfully")
    except Exception as exc:
        logger.error("Failed to load model: %s", exc)
        app.state.model = None

    try:
        app.state.db_pool = await create_pool()
        logger.info("Database pool created")
    except Exception as exc:
        logger.error("Failed to connect to database: %s", exc)
        app.state.db_pool = None

    from clients.kafka import KafkaProducer, KAFKA_BOOTSTRAP_SERVERS
    kafka_producer = KafkaProducer(KAFKA_BOOTSTRAP_SERVERS)
    try:
        await kafka_producer.start()
        app.state.kafka_producer = kafka_producer
        logger.info("Kafka producer started")
    except Exception as exc:
        logger.error("Failed to start Kafka producer: %s", exc)
        app.state.kafka_producer = None

    yield

    app.state.model = None
    if getattr(app.state, "db_pool", None) is not None:
        await app.state.db_pool.close()
        app.state.db_pool = None
    if getattr(app.state, "kafka_producer", None) is not None:
        await app.state.kafka_producer.stop()
        app.state.kafka_producer = None


app = FastAPI(lifespan=lifespan)
app.include_router(predict_router)
app.include_router(async_predict_router)


@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs"}
