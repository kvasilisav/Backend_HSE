import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

import main
from clients.kafka import KafkaProducer
from repositories.moderation_results import ModerationResultsRepository


@pytest.fixture
def mock_model():
    model = MagicMock()
    model.predict.return_value = [1]
    model.predict_proba.return_value = [[0.2, 0.8]]
    return model


@pytest.fixture
def client_with_mock_model(client, mock_model):
    original_model = getattr(main.app.state, "model", None)
    main.app.state.model = mock_model
    yield client
    main.app.state.model = original_model


@pytest.fixture
def db_client_with_mock_model(db_client, mock_model):
    client, pool = db_client
    original_model = getattr(main.app.state, "model", None)
    main.app.state.model = mock_model
    yield client, pool
    main.app.state.model = original_model


@pytest.mark.integration
@pytest.mark.asyncio
async def test_async_predict_create_task(db_client_with_mock_model):
    client, pool = db_client_with_mock_model
    from repositories.users import UsersRepository
    from repositories.ads import AdsRepository

    users = UsersRepository(pool)
    ads = AdsRepository(pool)
    user_id = await users.create(is_verified_seller=False)
    item_id = await ads.create(
        seller_id=user_id,
        name="Test",
        description="Test description",
        category=1,
        images_qty=0,
    )

    with patch("routes.async_predict.KafkaProducer") as mock_kafka:
        mock_producer = AsyncMock()
        mock_producer.send_moderation_request = AsyncMock()
        mock_kafka.return_value = mock_producer
        main.app.state.kafka_producer = mock_producer

        response = client.post("/async_predict", json={"item_id": item_id})
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "pending"
        assert data["message"] == "Moderation request accepted"
        assert mock_producer.send_moderation_request.call_args[0] == (item_id, data["task_id"])


@pytest.mark.integration
def test_async_predict_ad_not_found(db_client_with_mock_model):
    client, _ = db_client_with_mock_model
    with patch("routes.async_predict.KafkaProducer"):
        response = client.post("/async_predict", json={"item_id": 999999})
        assert response.status_code == 404


def test_async_predict_validation(client, monkeypatch):
    class MockPool:
        pass

    class MockKafka:
        async def start(self):
            pass

    monkeypatch.setattr(main.app.state, "db_pool", MockPool())
    monkeypatch.setattr(main.app.state, "kafka_producer", MockKafka())
    response = client.post("/async_predict", json={"item_id": -1})
    assert response.status_code == 422

    response = client.post("/async_predict", json={})
    assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_moderation_result_pending(db_client_with_mock_model):
    client, pool = db_client_with_mock_model
    from repositories.users import UsersRepository
    from repositories.ads import AdsRepository

    users = UsersRepository(pool)
    ads = AdsRepository(pool)
    user_id = await users.create(is_verified_seller=False)
    item_id = await ads.create(
        seller_id=user_id,
        name="Test",
        description="Test",
        category=1,
        images_qty=0,
    )

    results_repo = ModerationResultsRepository(pool)
    task_id = await results_repo.create(item_id)

    response = client.get(f"/moderation_result/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task_id
    assert data["status"] == "pending"
    assert data["is_violation"] is None
    assert data["probability"] is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_moderation_result_completed(db_client_with_mock_model):
    client, pool = db_client_with_mock_model
    from repositories.users import UsersRepository
    from repositories.ads import AdsRepository

    users = UsersRepository(pool)
    ads = AdsRepository(pool)
    user_id = await users.create(is_verified_seller=False)
    item_id = await ads.create(
        seller_id=user_id,
        name="Test",
        description="Test",
        category=1,
        images_qty=0,
    )

    results_repo = ModerationResultsRepository(pool)
    task_id = await results_repo.create(item_id)
    await results_repo.update_completed(task_id, True, 0.85)

    response = client.get(f"/moderation_result/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task_id
    assert data["status"] == "completed"
    assert data["is_violation"] is True
    assert data["probability"] == 0.85


def test_get_moderation_result_not_found(client, monkeypatch):
    class MockPool:
        async def fetchrow(self, query, task_id):
            return None

    async def mock_get_by_id(self, task_id):
        return None

    monkeypatch.setattr(main.app.state, "db_pool", MockPool())
    monkeypatch.setattr(
        ModerationResultsRepository, "get_by_id", mock_get_by_id
    )
    response = client.get("/moderation_result/999999")
    assert response.status_code == 404
