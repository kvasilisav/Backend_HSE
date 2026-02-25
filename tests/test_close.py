import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException

import main
from services.close_ad_service import close_ad


@pytest.fixture
def mock_pool():
    return MagicMock()


@pytest.fixture
def mock_cache():
    c = MagicMock()
    c.delete_many = AsyncMock()
    return c


@pytest.mark.asyncio
async def test_close_ad_not_found(mock_pool, mock_cache):
    from unittest.mock import patch
    import services.close_ad_service as close_svc

    with patch.object(close_svc.ModerationResultsRepository, "get_task_ids_by_item_id", new_callable=AsyncMock, return_value=[]):
        with patch.object(close_svc.ModerationResultsRepository, "delete_by_item_id", new_callable=AsyncMock):
            with patch.object(close_svc.AdsRepository, "close", new_callable=AsyncMock, return_value=False):
                with pytest.raises(HTTPException) as exc_info:
                    await close_ad(999, mock_pool, mock_cache)
                assert exc_info.value.status_code == 404


def test_close_validation(client, monkeypatch):
    monkeypatch.setattr(main.app.state, "db_pool", MagicMock())
    response = client.post("/close", json={"item_id": -1})
    assert response.status_code == 422
    response = client.post("/close", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_close_ad_success_deletes_cache(mock_pool, mock_cache):
    from unittest.mock import patch
    import services.close_ad_service as close_svc

    with patch.object(close_svc.ModerationResultsRepository, "get_task_ids_by_item_id", new_callable=AsyncMock, return_value=[1, 2]):
        with patch.object(close_svc.ModerationResultsRepository, "delete_by_item_id", new_callable=AsyncMock):
            with patch.object(close_svc.AdsRepository, "close", new_callable=AsyncMock, return_value=True):
                await close_ad(5, mock_pool, mock_cache)
    mock_cache.delete_many.assert_called_once()
    call_args = mock_cache.delete_many.call_args[0][0]
    assert "simple_predict:5" in call_args
    assert "moderation_result:1" in call_args
    assert "moderation_result:2" in call_args


@pytest.mark.integration
@pytest.mark.asyncio
async def test_close_ad_integration(db_client):
    from repositories.users import UsersRepository
    from repositories.ads import AdsRepository
    from repositories.moderation_results import ModerationResultsRepository

    client, pool = db_client
    users = UsersRepository(pool)
    ads = AdsRepository(pool)
    user_id = await users.create(is_verified_seller=False)
    item_id = await ads.create(
        seller_id=user_id,
        name="To close",
        description="Desc",
        category=1,
        images_qty=0,
    )
    results_repo = ModerationResultsRepository(pool)
    task_id = await results_repo.create(item_id)

    cache = getattr(main.app.state, "cache", None)
    response = client.post("/close", json={"item_id": item_id})
    assert response.status_code == 200

    ad = await ads.get_by_id(item_id)
    assert ad is None
    result = await results_repo.get_by_id(task_id)
    assert result is None
