from __future__ import annotations

from uuid import UUID

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from api.schemas.auth import RepositoryUser

USER_SELECT = """
    SELECT
        u.user_id,
        u.username,
        u.password_hash,
        u.is_active,
        COALESCE(
            array_agg(r.name ORDER BY r.name)
                FILTER (WHERE r.name IS NOT NULL),
            ARRAY[]::TEXT[]
        ) AS roles
    FROM security.users AS u
    LEFT JOIN security.user_roles AS ur
        ON ur.user_id = u.user_id
    LEFT JOIN security.roles AS r
        ON r.role_id = ur.role_id
"""


class UserRepository:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def get_by_username(self, username: str) -> RepositoryUser | None:
        return await self._get_user(
            f"{USER_SELECT} WHERE u.username = %s GROUP BY u.user_id",
            (username,),
        )

    async def get_by_user_id(self, user_id: UUID) -> RepositoryUser | None:
        return await self._get_user(
            f"{USER_SELECT} WHERE u.user_id = %s GROUP BY u.user_id",
            (user_id,),
        )

    async def _get_user(
        self,
        query: str,
        parameters: tuple[object, ...],
    ) -> RepositoryUser | None:
        async with self._pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(query, parameters)
                row = await cursor.fetchone()
        return None if row is None else RepositoryUser.model_validate(row)

    async def update_last_login_at(self, user_id: UUID) -> None:
        async with self._pool.connection() as connection:
            await connection.execute(
                """
                UPDATE security.users
                SET last_login_at = CURRENT_TIMESTAMP,
                    updated_at = GREATEST(updated_at, CURRENT_TIMESTAMP)
                WHERE user_id = %s
                """,
                (user_id,),
            )
