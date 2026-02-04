import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from db.connection import create_pool
from model import get_model
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

    yield

    app.state.model = None
    if getattr(app.state, "db_pool", None) is not None:
        await app.state.db_pool.close()
        app.state.db_pool = None


app = FastAPI(lifespan=lifespan)
app.include_router(predict_router)


@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs"}
