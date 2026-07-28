from __future__ import annotations

from psycopg_pool import AsyncConnectionPool

from api.config import Settings


def create_database_pool(settings: Settings) -> AsyncConnectionPool:
    return AsyncConnectionPool(
        kwargs=settings.database_connection_kwargs(),
        min_size=settings.database_pool_min_size,
        max_size=settings.database_pool_max_size,
        timeout=settings.database_pool_timeout,
        open=False,
    )
