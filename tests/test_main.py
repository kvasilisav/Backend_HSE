from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import main


def build_payload(**overrides):
    payload = {
        "seller_id": 123,
        "is_verified_seller": False,
        "item_id": 456,
        "name": "Phone",
        "description": "A good phone",
        "category": 7,
        "images_qty": 1,
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def client():
    with TestClient(main.app) as c:
        yield c


def test_predict_violation_true(client):
    payload = build_payload(is_verified_seller=False, images_qty=0, description="x" * 10)
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "is_violation" in data
    assert "probability" in data
    assert data["is_violation"] is True
    assert 0 <= data["probability"] <= 1


def test_predict_violation_false(client):
    payload = build_payload(
        is_verified_seller=True, images_qty=5, description="x" * 100, category=50
    )
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "is_violation" in data
    assert "probability" in data
    assert data["is_violation"] is False
    assert 0 <= data["probability"] <= 1


def test_predict_validation_errors(client):
    payload = build_payload()
    payload.pop("seller_id")
    response = client.post("/predict", json=payload)
    assert response.status_code == 422

    response = client.post("/predict", json=build_payload(images_qty="many"))
    assert response.status_code == 422

    response = client.post("/predict", json=build_payload(seller_id=-1))
    assert response.status_code == 422


def test_predict_model_unavailable(client):
    original_model = getattr(main.app.state, "model", None)
    main.app.state.model = None
    try:
        response = client.post("/predict", json=build_payload())
        assert response.status_code == 503
        assert response.json()["detail"] == "Model not loaded"
    finally:
        main.app.state.model = original_model
