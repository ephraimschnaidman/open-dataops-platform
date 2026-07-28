from __future__ import annotations

from psycopg_pool import AsyncConnectionPool


class HealthRepository:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def database_is_healthy(self) -> bool:
        async with self._pool.connection() as connection:
            result = await connection.execute("SELECT 1")
            row = await result.fetchone()
        return row == (1,)
