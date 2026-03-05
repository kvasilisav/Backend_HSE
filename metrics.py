import time
from typing import Any, Coroutine, TypeVar

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

PREDICTIONS_TOTAL = Counter(
    "predictions_total",
    "Total number of predictions",
    ["result"],
)
PREDICTION_DURATION_SECONDS = Histogram(
    "prediction_duration_seconds",
    "Time spent on ML model inference",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)
PREDICTION_ERRORS_TOTAL = Counter(
    "prediction_errors_total",
    "Number of prediction errors",
    ["error_type"],
)
DB_QUERY_DURATION_SECONDS = Histogram(
    "db_query_duration_seconds",
    "Time spent on PostgreSQL queries",
    ["query_type"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)
MODEL_PREDICTION_PROBABILITY = Histogram(
    "model_prediction_probability",
    "Distribution of violation probability from ML model",
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

T = TypeVar("T")


async def record_db_duration(query_type: str, coro: Coroutine[Any, Any, T]) -> T:
    start = time.perf_counter()
    try:
        return await coro
    finally:
        DB_QUERY_DURATION_SECONDS.labels(query_type=query_type).observe(
            time.perf_counter() - start
        )


def get_metrics_content() -> bytes:
    return generate_latest()


def get_metrics_content_type() -> str:
    return CONTENT_TYPE_LATEST
