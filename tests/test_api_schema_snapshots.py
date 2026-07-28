import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform"))

from api.main import app  # noqa: E402
from api.repositories.schema_snapshots import (  # noqa: E402
    SchemaSnapshotFilters,
    SchemaSnapshotRepository,
)
from api.routes.schema_snapshots import get_schema_snapshot_service  # noqa: E402
from api.schemas.schema_snapshots import (  # noqa: E402
    SchemaSnapshotListResponse,
    SchemaSnapshotPaginationMetadata,
    SchemaSnapshotResponse,
)
from api.services.schema_snapshots import SchemaSnapshotService  # noqa: E402

SNAPSHOT_ID = UUID("11111111-1111-4111-8111-111111111111")
SECOND_SNAPSHOT_ID = UUID("33333333-3333-4333-8333-333333333333")
PIPELINE_RUN_ID = UUID("22222222-2222-4222-8222-222222222222")
NOW = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)


def snapshot_data(**overrides):
    values = {
        "snapshot_id": SNAPSHOT_ID,
        "pipeline_run_id": PIPELINE_RUN_ID,
        "table_schema": "raw",
        "table_name": "orders",
        "column_name": "order_id",
        "ordinal_position": 1,
        "data_type": "text",
        "is_nullable": False,
        "measured_at": NOW,
        "created_at": NOW,
    }
    values.update(overrides)
    return values


class StubSchemaSnapshotService:
    def __init__(self):
        self.result = SchemaSnapshotListResponse(
            items=[SchemaSnapshotResponse(**snapshot_data())],
            pagination=SchemaSnapshotPaginationMetadata(
                limit=100,
                offset=0,
                total=1,
                returned_count=1,
            ),
        )
        self.error = None
        self.arguments = None

    async def list_schema_snapshots(self, **arguments):
        self.arguments = arguments
        if self.error:
            raise self.error
        return self.result


class StubSchemaSnapshotRepository:
    def __init__(self, rows=None, total=0):
        self.rows = [] if rows is None else rows
        self.total = total
        self.arguments = None

    async def list_schema_snapshots(self, **arguments):
        self.arguments = arguments
        return self.rows, self.total


class RecordingResult:
    async def fetchone(self):
        return (0,)


class RecordingCursor:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False

    async def execute(self, query, parameters):
        self.connection.list_query = query
        self.connection.list_parameters = parameters

    async def fetchall(self):
        return []


class RecordingConnection:
    def __init__(self):
        self.count_query = None
        self.count_parameters = None
        self.list_query = None
        self.list_parameters = None

    async def execute(self, query, parameters):
        self.count_query = query
        self.count_parameters = parameters
        return RecordingResult()

    def cursor(self, row_factory=None):
        return RecordingCursor(self)


class RecordingConnectionContext:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False


class RecordingPool:
    def __init__(self):
        self.connection_instance = RecordingConnection()

    def connection(self):
        return RecordingConnectionContext(self.connection_instance)


class SchemaSnapshotApiRouteTests(unittest.TestCase):
    def setUp(self):
        self.service = StubSchemaSnapshotService()
        app.dependency_overrides[get_schema_snapshot_service] = lambda: self.service
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()

    def test_historical_list_success(self):
        response = self.client.get("/api/v1/schema-snapshots")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["items"][0]["snapshot_id"],
            str(SNAPSHOT_ID),
        )
        self.assertFalse(self.service.arguments["latest"])

    def test_empty_result(self):
        self.service.result = SchemaSnapshotListResponse(
            items=[],
            pagination=SchemaSnapshotPaginationMetadata(
                limit=100,
                offset=0,
                total=0,
                returned_count=0,
            ),
        )

        response = self.client.get("/api/v1/schema-snapshots")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"], [])
        self.assertEqual(response.json()["pagination"]["total"], 0)
        self.assertEqual(response.json()["pagination"]["returned_count"], 0)

    def test_pagination_parameters(self):
        response = self.client.get(
            "/api/v1/schema-snapshots?limit=250&offset=500"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.service.arguments["limit"], 250)
        self.assertEqual(self.service.arguments["offset"], 500)

    def test_pipeline_run_id_filter(self):
        response = self.client.get(
            f"/api/v1/schema-snapshots?pipeline_run_id={PIPELINE_RUN_ID}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.service.arguments["filters"].pipeline_run_id,
            PIPELINE_RUN_ID,
        )

    def test_table_schema_filter(self):
        response = self.client.get(
            "/api/v1/schema-snapshots?table_schema=raw"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.service.arguments["filters"].table_schema, "raw")

    def test_table_name_filter(self):
        response = self.client.get(
            "/api/v1/schema-snapshots?table_name=orders"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.service.arguments["filters"].table_name, "orders")

    def test_column_name_filter(self):
        response = self.client.get(
            "/api/v1/schema-snapshots?column_name=order_id"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.service.arguments["filters"].column_name,
            "order_id",
        )

    def test_combined_filters(self):
        response = self.client.get(
            "/api/v1/schema-snapshots"
            f"?pipeline_run_id={PIPELINE_RUN_ID}"
            "&table_schema=raw&table_name=orders&column_name=order_id"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.service.arguments["filters"],
            SchemaSnapshotFilters(
                pipeline_run_id=PIPELINE_RUN_ID,
                table_schema="raw",
                table_name="orders",
                column_name="order_id",
            ),
        )

    def test_invalid_limit_returns_422(self):
        for limit in ("0", "501"):
            with self.subTest(limit=limit):
                response = self.client.get(
                    f"/api/v1/schema-snapshots?limit={limit}"
                )
                self.assertEqual(response.status_code, 422)

    def test_invalid_offset_returns_422(self):
        response = self.client.get("/api/v1/schema-snapshots?offset=-1")

        self.assertEqual(response.status_code, 422)

    def test_invalid_pipeline_uuid_returns_422(self):
        response = self.client.get(
            "/api/v1/schema-snapshots?pipeline_run_id=not-a-uuid"
        )

        self.assertEqual(response.status_code, 422)

    def test_database_error_returns_safe_503(self):
        self.service.error = RuntimeError("SELECT secret FROM hidden")

        response = self.client.get("/api/v1/schema-snapshots")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Database unavailable"})
        self.assertNotIn("SELECT", response.text)

    def test_latest_true_is_passed_to_service(self):
        response = self.client.get("/api/v1/schema-snapshots?latest=true")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.service.arguments["latest"])

    def test_response_schema_requires_positive_ordinal_position(self):
        with self.assertRaises(ValidationError):
            SchemaSnapshotResponse(**snapshot_data(ordinal_position=0))


class SchemaSnapshotServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_latest_multiple_tables_and_all_columns_are_preserved(self):
        rows = [
            snapshot_data(),
            snapshot_data(
                snapshot_id=SECOND_SNAPSHOT_ID,
                column_name="created_at",
                ordinal_position=2,
            ),
            snapshot_data(
                snapshot_id=UUID("44444444-4444-4444-8444-444444444444"),
                table_name="customers",
                column_name="customer_id",
            ),
        ]
        repository = StubSchemaSnapshotRepository(rows=rows, total=3)

        result = await SchemaSnapshotService(
            repository
        ).list_schema_snapshots(
            limit=100,
            offset=0,
            filters=SchemaSnapshotFilters(),
            latest=True,
        )

        self.assertEqual(result.pagination.total, 3)
        self.assertEqual(result.pagination.returned_count, 3)
        self.assertEqual(
            [item.column_name for item in result.items[:2]],
            ["order_id", "created_at"],
        )
        self.assertTrue(repository.arguments["latest"])


class SchemaSnapshotRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_latest_query_joins_all_columns_from_one_selected_run(self):
        pool = RecordingPool()
        repository = SchemaSnapshotRepository(pool)

        await repository.list_schema_snapshots(
            limit=100,
            offset=0,
            filters=SchemaSnapshotFilters(
                table_schema="raw",
                table_name="orders",
                column_name="order_id",
            ),
            latest=True,
        )

        query = pool.connection_instance.list_query
        selector = query.split(")")[0]
        self.assertIn("DISTINCT ON (table_schema, table_name)", query)
        self.assertIn("latest.pipeline_run_id = s.pipeline_run_id", query)
        self.assertIn("latest.table_schema = s.table_schema", query)
        self.assertIn("latest.table_name = s.table_name", query)
        self.assertNotIn("column_name = %s", selector)
        self.assertIn("s.column_name = %s", query)

    async def test_latest_with_pipeline_run_does_not_switch_runs(self):
        pool = RecordingPool()
        repository = SchemaSnapshotRepository(pool)

        await repository.list_schema_snapshots(
            limit=100,
            offset=0,
            filters=SchemaSnapshotFilters(pipeline_run_id=PIPELINE_RUN_ID),
            latest=True,
        )

        query = pool.connection_instance.list_query
        self.assertNotIn("DISTINCT ON", query)
        self.assertIn("pipeline_run_id = %s", query)
        self.assertEqual(
            pool.connection_instance.list_parameters,
            [PIPELINE_RUN_ID, 100, 0],
        )

    async def test_latest_query_has_deterministic_column_ordering(self):
        pool = RecordingPool()

        await SchemaSnapshotRepository(pool).list_schema_snapshots(
            limit=100,
            offset=0,
            filters=SchemaSnapshotFilters(),
            latest=True,
        )

        query = " ".join(pool.connection_instance.list_query.split())
        self.assertIn(
            "ORDER BY s.table_schema ASC, s.table_name ASC, "
            "s.ordinal_position ASC, s.snapshot_id DESC",
            query,
        )


if __name__ == "__main__":
    unittest.main()
