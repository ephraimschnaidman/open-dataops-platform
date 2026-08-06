from __future__ import annotations

import csv
import io
import os

from .docker import DockerClient
from .command import CommandError
from .timing import wait_until


class PostgresClient:
    def __init__(self, docker: DockerClient, service: str = "postgres"):
        self.docker = docker
        self.service = service
        self.database = os.getenv("POSTGRES_DB", "dataops")
        self.user = os.getenv("POSTGRES_USER", "dataops")

    def stop_postgres(self):
        return self.docker.stop_service(self.service)

    def start_postgres(self):
        return self.docker.start_service(self.service)

    def wait_for_postgres_ready(self, timeout: float) -> bool:
        def ready() -> bool:
            try:
                result = self.docker.compose_exec(self.service, ["pg_isready", "-U", self.user, "-d", self.database], timeout=10)
                return result.return_code == 0
            except CommandError:
                return False
        return wait_until(ready, timeout, 2.0, "PostgreSQL readiness")

    def execute_read_only_query(self, sql: str) -> list[list[str]]:
        statement = sql.strip().lower()
        if not (statement.startswith("select") or statement.startswith("with")) or ";" in statement.rstrip(";"):
            raise ValueError("Only one SELECT or WITH query is allowed")
        result = self.docker.compose_exec(self.service,
            ["env", "PGOPTIONS=--default_transaction_read_only=on", "psql", "-X", "--csv",
             "-v", "ON_ERROR_STOP=1", "-U", self.user, "-d", self.database, "-c", sql])
        return list(csv.reader(io.StringIO(result.stdout)))

    def database_size(self) -> str:
        rows = self.execute_read_only_query(f"SELECT pg_size_pretty(pg_database_size('{self.database}')) AS size")
        return rows[1][0] if len(rows) > 1 else "unknown"

    def scalar_read_only_query(self, sql: str) -> str:
        rows = self.execute_read_only_query(sql)
        if len(rows) != 2 or len(rows[1]) != 1:
            raise ValueError("Expected a query returning exactly one scalar row")
        return rows[1][0]

    def table_row_counts(self, tables: list[str]) -> dict[str, int]:
        counts = {}
        for table in tables:
            if not table.replace("_", "").replace(".", "").isalnum():
                raise ValueError(f"Invalid table name: {table}")
            rows = self.execute_read_only_query(f"SELECT count(*) AS count FROM {table}")
            counts[table] = int(rows[1][0])
        return counts
