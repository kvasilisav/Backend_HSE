import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from repositories.ads import AdsRepository
from repositories.moderation_results import ModerationResultsRepository

from workers.moderation_worker import process_message, MAX_RETRIES


@pytest.fixture
def mock_model():
    m = MagicMock()
    m.predict.return_value = [0]
    m.predict_proba.return_value = [[0.9, 0.1]]
    return m


@pytest.fixture
def mock_pool():
    return MagicMock()


@pytest.fixture
def mock_kafka():
    k = AsyncMock()
    k.send_to_dlq = AsyncMock()
    return k


@pytest.mark.asyncio
async def test_process_message_success(mock_model, mock_pool, mock_kafka):
    ad_row = {
        "id": 1,
        "seller_id": 10,
        "is_verified_seller": True,
        "description": "x",
        "category": 1,
        "images_qty": 0,
    }
    with patch.object(AdsRepository, "get_by_id", new_callable=AsyncMock, return_value=ad_row):
        with patch.object(
            ModerationResultsRepository, "update_completed", new_callable=AsyncMock
        ) as update_completed:
            with patch(
                "workers.moderation_worker.run_prediction", return_value=(False, 0.1)
            ):
                msg = {"item_id": 1, "task_id": 100, "timestamp": "2025-01-01T00:00:00Z"}
                await process_message(msg, mock_model, mock_pool, mock_kafka)
    update_completed.assert_called_once_with(100, False, 0.1)
    mock_kafka.send_to_dlq.assert_not_called()


@pytest.mark.asyncio
async def test_process_message_ad_not_found_sends_dlq(mock_model, mock_pool, mock_kafka):
    with patch.object(AdsRepository, "get_by_id", new_callable=AsyncMock, return_value=None):
        with patch.object(
            ModerationResultsRepository, "update_failed", new_callable=AsyncMock
        ) as update_failed:
            msg = {"item_id": 999, "task_id": 1, "timestamp": "2025-01-01T00:00:00Z"}
            await process_message(msg, mock_model, mock_pool, mock_kafka)
    update_failed.assert_called_once_with(1, "Ad with item_id=999 not found")
    mock_kafka.send_to_dlq.assert_called_once()
    call_args = mock_kafka.send_to_dlq.call_args[0]
    assert call_args[0] == msg
    assert "not found" in call_args[1]
    assert call_args[2] == 0


@pytest.mark.asyncio
async def test_process_message_missing_task_id_returns(mock_model, mock_pool, mock_kafka):
    msg = {"item_id": 1, "timestamp": "2025-01-01T00:00:00Z"}
    await process_message(msg, mock_model, mock_pool, mock_kafka)
    mock_kafka.send_to_dlq.assert_not_called()


@pytest.mark.asyncio
async def test_process_message_retry_then_dlq(mock_model, mock_pool, mock_kafka):
    ad_row = {
        "id": 1,
        "seller_id": 1,
        "is_verified_seller": False,
        "description": "x",
        "category": 1,
        "images_qty": 0,
    }
    with patch.object(AdsRepository, "get_by_id", new_callable=AsyncMock, return_value=ad_row):
        with patch(
            "workers.moderation_worker.run_prediction", side_effect=RuntimeError("model down")
        ):
            with patch.object(
                ModerationResultsRepository, "update_failed", new_callable=AsyncMock
            ):
                with patch("workers.moderation_worker.asyncio.sleep", new_callable=AsyncMock):
                    msg = {"item_id": 1, "task_id": 1, "timestamp": "2025-01-01T00:00:00Z"}
                    await process_message(msg, mock_model, mock_pool, mock_kafka)
    assert mock_kafka.send_to_dlq.call_count == 1
    call_args = mock_kafka.send_to_dlq.call_args[0]
    assert call_args[2] == MAX_RETRIES
