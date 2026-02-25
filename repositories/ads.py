import asyncpg


class AdsRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def get_by_id(self, item_id: int):
        return await self.pool.fetchrow(
            """
            SELECT a.id, a.seller_id, a.name, a.description, a.category, a.images_qty,
                   u.is_verified_seller
            FROM ads a
            INNER JOIN users u ON a.seller_id = u.id
            WHERE a.id = $1 AND a.is_closed = FALSE
            """,
            item_id,
        )

    async def close(self, item_id: int) -> bool:
        row = await self.pool.fetchrow(
            "UPDATE ads SET is_closed = TRUE WHERE id = $1 AND is_closed = FALSE RETURNING id",
            item_id,
        )
        return row is not None

    async def create(
        self,
        seller_id: int,
        name: str,
        description: str,
        category: int,
        images_qty: int = 0,
    ) -> int:
        row = await self.pool.fetchrow(
            """
            INSERT INTO ads (seller_id, name, description, category, images_qty)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
            """,
            seller_id,
            name,
            description,
            category,
            images_qty,
        )
        return row["id"]
