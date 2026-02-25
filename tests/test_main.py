import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

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
def mock_model():
    model = MagicMock()
    model.predict.return_value = [1]
    model.predict_proba.return_value = [[0.2, 0.8]]
    return model


@pytest.fixture
def mock_model_false():
    model = MagicMock()
    model.predict.return_value = [0]
    model.predict_proba.return_value = [[0.9, 0.1]]
    return model


@pytest.fixture
def client_with_mock_model(client, mock_model):
    original_model = getattr(main.app.state, "model", None)
    main.app.state.model = mock_model
    yield client
    main.app.state.model = original_model


@pytest.fixture
def client_with_mock_model_false(client, mock_model_false):
    original_model = getattr(main.app.state, "model", None)
    main.app.state.model = mock_model_false
    yield client
    main.app.state.model = original_model


def test_predict_violation_true(client_with_mock_model):
    payload = build_payload()
    response = client_with_mock_model.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "is_violation" in data
    assert "probability" in data
    assert data["is_violation"] is True
    assert data["probability"] == 0.8


def test_predict_violation_false(client_with_mock_model_false):
    payload = build_payload()
    response = client_with_mock_model_false.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "is_violation" in data
    assert "probability" in data
    assert data["is_violation"] is False
    assert data["probability"] == 0.1


def test_predict_validation_errors(client):
    payload = build_payload()
    payload.pop("seller_id")
    response = client.post("/predict", json=payload)
    assert response.status_code == 422

    response = client.post("/predict", json=build_payload(images_qty="many"))
    assert response.status_code == 422

    response = client.post("/predict", json=build_payload(seller_id=-1))
    assert response.status_code == 422


@pytest.fixture
def client_without_model(client):
    original_model = getattr(main.app.state, "model", None)
    main.app.state.model = None
    yield client
    main.app.state.model = original_model


def test_predict_model_unavailable(client_without_model):
    response = client_without_model.post("/predict", json=build_payload())
    assert response.status_code == 503
    assert response.json()["detail"] == "Model not loaded"


@pytest.fixture
def db_client_with_mock_model(db_client, mock_model):
    client, pool = db_client
    original_model = getattr(main.app.state, "model", None)
    main.app.state.model = mock_model
    yield client, pool
    main.app.state.model = original_model


@pytest.fixture
def db_client_with_mock_model_false(db_client, mock_model_false):
    client, pool = db_client
    original_model = getattr(main.app.state, "model", None)
    main.app.state.model = mock_model_false
    yield client, pool
    main.app.state.model = original_model


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


@pytest.mark.integration
@pytest.mark.asyncio
async def test_simple_predict_violation_true(db_client_with_mock_model):
    client, pool = db_client_with_mock_model
    item_id = await _create_ad(pool, False, 10, 7, 0)
    response = client.post("/simple_predict", json={"item_id": item_id})
    assert response.status_code == 200
    data = response.json()
    assert data["is_violation"] is True
    assert data["probability"] == 0.8


@pytest.mark.integration
@pytest.mark.asyncio
async def test_simple_predict_violation_false(db_client_with_mock_model_false):
    client, pool = db_client_with_mock_model_false
    item_id = await _create_ad(pool, True, 100, 50, 5)
    response = client.post("/simple_predict", json={"item_id": item_id})
    assert response.status_code == 200
    data = response.json()
    assert data["is_violation"] is False
    assert data["probability"] == 0.1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_simple_predict_ad_not_found(db_client_with_mock_model):
    client, _ = db_client_with_mock_model
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


@pytest.mark.integration
@pytest.mark.asyncio
async def test_repositories_create_user(db_client):
    _, pool = db_client
    users = UsersRepository(pool)
    user_id = await users.create(is_verified_seller=True)
    user = await users.get_by_id(user_id)
    assert user is not None
    assert user["is_verified_seller"] is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_repositories_create_ad(db_client):
    _, pool = db_client
    users = UsersRepository(pool)
    ads = AdsRepository(pool)
    user_id = await users.create(is_verified_seller=True)
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
