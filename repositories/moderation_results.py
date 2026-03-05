import asyncpg

from metrics import record_db_duration


class ModerationResultsRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def create(self, item_id: int) -> int:
        row = await record_db_duration(
            "insert",
            self.pool.fetchrow(
                """
                INSERT INTO moderation_results (item_id, status)
                VALUES ($1, 'pending')
                RETURNING id
                """,
                item_id,
            ),
        )
        return row["id"]

    async def get_by_id(self, task_id: int):
        return await record_db_duration(
            "select",
            self.pool.fetchrow(
                """
                SELECT id, item_id, status, is_violation, probability, error_message,
                       created_at, processed_at
                FROM moderation_results
                WHERE id = $1
                """,
                task_id,
            ),
        )

    async def update_completed(
        self, task_id: int, is_violation: bool, probability: float
    ):
        await record_db_duration(
            "update",
            self.pool.execute(
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
            ),
        )

    async def update_failed(self, task_id: int, error_message: str):
        await record_db_duration(
            "update",
            self.pool.execute(
                """
                UPDATE moderation_results
                SET status = 'failed',
                    error_message = $1,
                    processed_at = CURRENT_TIMESTAMP
                WHERE id = $2
                """,
                error_message,
                task_id,
            ),
        )

    async def get_task_ids_by_item_id(
        self, item_id: int, conn: asyncpg.Connection | None = None
    ) -> list[int]:
        conn_or_pool = conn if conn is not None else self.pool
        rows = await record_db_duration(
            "select",
            conn_or_pool.fetch(
                "SELECT id FROM moderation_results WHERE item_id = $1",
                item_id,
            ),
        )
        return [r["id"] for r in rows]

    async def delete_by_item_id(self, item_id: int, conn: asyncpg.Connection | None = None):
        conn_or_pool = conn if conn is not None else self.pool
        await record_db_duration(
            "delete",
            conn_or_pool.execute(
                "DELETE FROM moderation_results WHERE item_id = $1",
                item_id,
            ),
        )
