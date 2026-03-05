import logging
import time

import numpy as np

from metrics import (
    MODEL_PREDICTION_PROBABILITY,
    PREDICTION_DURATION_SECONDS,
    PREDICTIONS_TOTAL,
)

logger = logging.getLogger(__name__)


def build_features(
    is_verified_seller: bool,
    images_qty: int,
    description_length: int,
    category: int,
) -> np.ndarray:
    return np.array(
        [
            float(is_verified_seller),
            images_qty / 10.0,
            description_length / 1000.0,
            category / 100.0,
        ]
    ).reshape(1, -1)


def predict(model, features: np.ndarray) -> tuple[bool, float]:
    pred = model.predict(features)[0]
    proba = model.predict_proba(features)[0]
    proba_violation = float(proba[1])
    return bool(pred), proba_violation


def run_prediction(
    model,
    seller_id: int,
    is_verified_seller: bool,
    item_id: int,
    description: str,
    category: int,
    images_qty: int,
) -> tuple[bool, float]:
    features = build_features(
        is_verified_seller=is_verified_seller,
        images_qty=images_qty,
        description_length=len(description),
        category=category,
    )
    logger.info(
        "Request: seller_id=%s, item_id=%s, features=%s",
        seller_id,
        item_id,
        features.tolist(),
    )
    start = time.perf_counter()
    is_violation, probability = predict(model, features)
    PREDICTION_DURATION_SECONDS.observe(time.perf_counter() - start)
    result_label = "violation" if is_violation else "no_violation"
    PREDICTIONS_TOTAL.labels(result=result_label).inc()
    MODEL_PREDICTION_PROBABILITY.observe(probability)
    logger.info(
        "Prediction: is_violation=%s, probability=%s",
        is_violation,
        probability,
    )
    return is_violation, probability
