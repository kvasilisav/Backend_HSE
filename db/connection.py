import os

import asyncpg

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://moderation:moderation@localhost:5432/moderation",
)


async def create_pool():
    return await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
