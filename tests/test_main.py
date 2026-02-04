import asyncio
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main
from repositories.ads import AdsRepository
from repositories.users import UsersRepository


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


@pytest.fixture
def db_client(client):
    pool = getattr(main.app.state, "db_pool", None)
    if pool is None:
        pytest.skip("Database not available")
    return client, pool


async def _create_ad(pool, is_verified: bool, desc_len: int, category: int, images: int):
    users = UsersRepository(pool)
    ads = AdsRepository(pool)
    user_id = await users.create(is_verified_seller=is_verified)
    return await ads.create(
        seller_id=user_id,
        name="Test",
        description="x" * desc_len,
        category=category,
        images_qty=images,
    )


def test_simple_predict_violation_true(db_client):
    client, pool = db_client
    item_id = asyncio.run(_create_ad(pool, False, 10, 7, 0))
    response = client.post("/simple_predict", json={"item_id": item_id})
    assert response.status_code == 200
    data = response.json()
    assert data["is_violation"] is True
    assert 0 <= data["probability"] <= 1


def test_simple_predict_violation_false(db_client):
    client, pool = db_client
    item_id = asyncio.run(_create_ad(pool, True, 100, 50, 5))
    response = client.post("/simple_predict", json={"item_id": item_id})
    assert response.status_code == 200
    data = response.json()
    assert data["is_violation"] is False
    assert 0 <= data["probability"] <= 1


def test_simple_predict_ad_not_found(db_client):
    client, _ = db_client
    response = client.post("/simple_predict", json={"item_id": 999999})
    assert response.status_code == 404


def test_simple_predict_validation(client, monkeypatch):
    class MockPool:
        pass

    monkeypatch.setattr(main.app.state, "db_pool", MockPool())
    response = client.post("/simple_predict", json={"item_id": -1})
    assert response.status_code == 422

    response = client.post("/simple_predict", json={})
    assert response.status_code == 422


def test_simple_predict_ad_not_found_mock(client, monkeypatch):
    class MockPool:
        pass

    async def mock_get_by_id(item_id):
        return None

    monkeypatch.setattr(main.app.state, "db_pool", MockPool())
    monkeypatch.setattr(AdsRepository, "get_by_id", lambda s, i: mock_get_by_id(i))
    response = client.post("/simple_predict", json={"item_id": 999999})
    assert response.status_code == 404
    assert response.json()["detail"] == "Ad not found"


def test_repositories_create_user_and_ad(db_client):
    _, pool = db_client

    async def run():
        users = UsersRepository(pool)
        ads = AdsRepository(pool)
        user_id = await users.create(is_verified_seller=True)
        user = await users.get_by_id(user_id)
        assert user["is_verified_seller"] is True
        item_id = await ads.create(
            seller_id=user_id,
            name="Item",
            description="Desc",
            category=1,
            images_qty=3,
        )
        ad = await ads.get_by_id(item_id)
        assert ad["name"] == "Item"
        assert ad["description"] == "Desc"
        assert ad["category"] == 1
        assert ad["images_qty"] == 3
        assert ad["is_verified_seller"] is True

    asyncio.run(run())
