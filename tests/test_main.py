from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import main


client = TestClient(main.app)


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


def test_predict_positive_verified_seller():
    payload = build_payload(is_verified_seller=True, images_qty=0)
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    assert response.json() is True


def test_predict_positive_unverified_with_images():
    payload = build_payload(is_verified_seller=False, images_qty=2)
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    assert response.json() is True


def test_predict_negative_unverified_without_images():
    payload = build_payload(is_verified_seller=False, images_qty=0)
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    assert response.json() is False


def test_predict_validation_errors():
    payload = build_payload()
    payload.pop("seller_id")
    response = client.post("/predict", json=payload)
    assert response.status_code == 422

    response = client.post("/predict", json=build_payload(images_qty="many"))
    assert response.status_code == 422


def test_predict_business_error(monkeypatch):
    def _boom(_payload):
        raise RuntimeError("boom")

    monkeypatch.setattr(main, "predict_decision", _boom)
    response = client.post("/predict", json=build_payload())
    assert response.status_code == 500
    assert response.json()["detail"] == "Prediction failed"
