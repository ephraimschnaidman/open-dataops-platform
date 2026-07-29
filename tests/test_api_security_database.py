import os
import sys
import unittest
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg.errors import CheckViolation, ForeignKeyViolation

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform"))

from api.config import Settings  # noqa: E402


@unittest.skipUnless(
    os.getenv("RUN_API_DB_INTEGRATION") == "1",
    "Set RUN_API_DB_INTEGRATION=1 to run PostgreSQL security tests",
)
class SecurityDatabaseIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = Settings.from_environment()
        migration_path = (
            Path(__file__).resolve().parents[1]
            / "platform"
            / "warehouse"
            / "init"
            / "10_create_security_tables.sql"
        )
        cls.migration_sql = migration_path.read_text(encoding="utf-8")

    def connect(self):
        return psycopg.connect(
            **self.settings.database_connection_kwargs()
        )

    def test_migration_reruns_and_seeds_exact_roles(self):
        with self.connect() as connection:
            connection.execute(self.migration_sql)
            connection.execute(self.migration_sql)
            tables = connection.execute(
                """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'security'
                ORDER BY tablename
                """
            ).fetchall()
            roles = connection.execute(
                "SELECT name, COUNT(*) FROM security.roles "
                "GROUP BY name ORDER BY name"
            ).fetchall()
        self.assertEqual(
            tables,
            [("roles",), ("user_roles",), ("users",)],
        )
        self.assertEqual(
            roles,
            [("Admin", 1), ("Operator", 1), ("ReadOnly", 1)],
        )

    def test_username_and_password_constraints(self):
        cases = (
            ("UpperCase", "encoded-hash"),
            ("ab", "encoded-hash"),
            ("valid.user", "   "),
        )
        for username, encoded_hash in cases:
            with self.subTest(username=username, encoded_hash=encoded_hash):
                with self.connect() as connection:
                    with self.assertRaises(CheckViolation):
                        connection.execute(
                            """
                            INSERT INTO security.users
                                (username, password_hash)
                            VALUES (%s, %s)
                            """,
                            (username, encoded_hash),
                        )

    def test_user_role_foreign_keys_cascade_and_restrict(self):
        username = f"phase2.fk.{uuid4().hex}"
        with self.connect() as connection:
            user_id = connection.execute(
                """
                INSERT INTO security.users (username, password_hash)
                VALUES (%s, %s)
                RETURNING user_id
                """,
                (username, "$argon2id$integration-test"),
            ).fetchone()[0]
            role_id = connection.execute(
                "SELECT role_id FROM security.roles WHERE name = 'ReadOnly'"
            ).fetchone()[0]
            connection.execute(
                """
                INSERT INTO security.user_roles (user_id, role_id)
                VALUES (%s, %s)
                """,
                (user_id, role_id),
            )
            with self.assertRaises(ForeignKeyViolation):
                with connection.transaction():
                    connection.execute(
                        "DELETE FROM security.roles WHERE role_id = %s",
                        (role_id,),
                    )
            connection.execute(
                "DELETE FROM security.users WHERE user_id = %s",
                (user_id,),
            )
            assignment_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM security.user_roles
                WHERE user_id = %s
                """,
                (user_id,),
            ).fetchone()[0]
        self.assertEqual(assignment_count, 0)

    def test_grafana_reader_has_no_security_privileges(self):
        with self.connect() as connection:
            privileges = connection.execute(
                """
                SELECT
                    has_schema_privilege(
                        'grafana_reader', 'security', 'USAGE'
                    ),
                    has_table_privilege(
                        'grafana_reader', 'security.users', 'SELECT'
                    ),
                    has_table_privilege(
                        'grafana_reader', 'security.roles', 'SELECT'
                    ),
                    has_table_privilege(
                        'grafana_reader',
                        'security.user_roles',
                        'SELECT'
                    )
                """
            ).fetchone()
        self.assertEqual(privileges, (False, False, False, False))


if __name__ == "__main__":
    unittest.main()
