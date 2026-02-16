import asyncpg
from datetime import datetime


class ModerationResultsRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def create(self, item_id: int) -> int:
        row = await self.pool.fetchrow(
            """
            INSERT INTO moderation_results (item_id, status)
            VALUES ($1, 'pending')
            RETURNING id
            """,
            item_id,
        )
        return row["id"]

    async def get_by_id(self, task_id: int):
        return await self.pool.fetchrow(
            """
            SELECT id, item_id, status, is_violation, probability, error_message,
                   created_at, processed_at
            FROM moderation_results
            WHERE id = $1
            """,
            task_id,
        )

    async def update_completed(
        self, task_id: int, is_violation: bool, probability: float
    ):
        await self.pool.execute(
            """
            UPDATE moderation_results
            SET status = 'completed',
                is_violation = $1,
                probability = $2,
                processed_at = CURRENT_TIMESTAMP
            WHERE id = $3
            """,
            is_violation,
            probability,
            task_id,
        )

    async def update_failed(self, task_id: int, error_message: str):
        await self.pool.execute(
            """
            UPDATE moderation_results
            SET status = 'failed',
                error_message = $1,
                processed_at = CURRENT_TIMESTAMP
            WHERE id = $2
            """,
            error_message,
            task_id,
        )
