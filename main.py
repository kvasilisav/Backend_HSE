import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

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
    yield
    app.state.model = None


app = FastAPI(lifespan=lifespan)
app.include_router(predict_router)


@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs"}
