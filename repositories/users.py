import asyncpg


class UsersRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def get_by_id(self, user_id: int):
        return await self.pool.fetchrow(
            "SELECT id, is_verified_seller FROM users WHERE id = $1",
            user_id,
        )

    async def create(self, is_verified_seller: bool) -> int:
        row = await self.pool.fetchrow(
            "INSERT INTO users (is_verified_seller) VALUES ($1) RETURNING id",
            is_verified_seller,
        )
        return row["id"]
