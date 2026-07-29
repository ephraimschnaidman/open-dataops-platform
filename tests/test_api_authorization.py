import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform"))

from api.auth_dependencies import (  # noqa: E402
    get_current_active_user,
    get_user_repository,
    require_roles,
)
from api.config import Settings  # noqa: E402
from api.main import app, create_app  # noqa: E402
from api.routes.dbt_metadata import get_dbt_metadata_service  # noqa: E402
from api.routes.health import get_health_service  # noqa: E402
from api.routes.incidents import get_incident_service  # noqa: E402
from api.routes.metrics import get_metric_service  # noqa: E402
from api.routes.pipelines import get_pipeline_service  # noqa: E402
from api.routes.schema_snapshots import (  # noqa: E402
    get_schema_snapshot_service,
)
from api.schemas.auth import CurrentUser  # noqa: E402
from api.schemas.dbt_metadata import (  # noqa: E402
    DbtMetadataListResponse,
    DbtMetadataPaginationMetadata,
)
from api.schemas.health import HealthResponse  # noqa: E402
from api.schemas.incidents import IncidentListResponse, PaginationMetadata  # noqa: E402
from api.schemas.metrics import (  # noqa: E402
    MetricListResponse,
    MetricPaginationMetadata,
)
from api.schemas.pipelines import (  # noqa: E402
    PipelineListResponse,
    PipelinePaginationMetadata,
)
from api.schemas.schema_snapshots import (  # noqa: E402
    SchemaSnapshotListResponse,
    SchemaSnapshotPaginationMetadata,
)
from api.security import create_access_token  # noqa: E402
from api.services.incidents import IncidentNotFoundError  # noqa: E402

USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
PROTECTED_PATHS = (
    "/api/v1/incidents",
    "/api/v1/metrics",
    "/api/v1/schema-snapshots",
    "/api/v1/dbt-metadata",
    "/api/v1/pipelines",
)


def make_settings(**overrides):
    values = {
        "jwt_secret_key": (
            "phase-4-test-secret-with-more-than-32-characters"
        ),
        "jwt_issuer": "open-dataops-platform-api",
        "jwt_audience": "open-dataops-platform-clients",
        "api_docs_enabled": True,
    }
    values.update(overrides)
    return Settings(**values)


def active_user(role):
    return CurrentUser(
        user_id=USER_ID,
        username=f"{role.lower()}.user",
        is_active=True,
        roles=[role],
    )


class EmptyOperationalService:
    def __init__(self):
        self.called = False

    async def list_incidents(self, **arguments):
        self.called = True
        return IncidentListResponse(
            items=[],
            pagination=PaginationMetadata(
                limit=arguments["limit"],
                offset=arguments["offset"],
                total=0,
                returned_count=0,
            ),
        )

    async def get_incident(self, incident_id):
        self.called = True
        raise IncidentNotFoundError

    async def list_metrics(self, **arguments):
        self.called = True
        return MetricListResponse(
            items=[],
            pagination=MetricPaginationMetadata(
                limit=arguments["limit"],
                offset=arguments["offset"],
                total=0,
                returned_count=0,
            ),
        )

    async def list_schema_snapshots(self, **arguments):
        self.called = True
        return SchemaSnapshotListResponse(
            items=[],
            pagination=SchemaSnapshotPaginationMetadata(
                limit=arguments["limit"],
                offset=arguments["offset"],
                total=0,
                returned_count=0,
            ),
        )

    async def list_dbt_metadata(self, **arguments):
        self.called = True
        return DbtMetadataListResponse(
            items=[],
            pagination=DbtMetadataPaginationMetadata(
                limit=arguments["limit"],
                offset=arguments["offset"],
                total=0,
                returned_count=0,
            ),
        )

    async def list_pipelines(self, **arguments):
        self.called = True
        return PipelineListResponse(
            items=[],
            pagination=PipelinePaginationMetadata(
                limit=arguments["limit"],
                offset=arguments["offset"],
                total=0,
                returned_count=0,
            ),
        )


class StubHealthService:
    async def check(self):
        return HealthResponse(
            status="healthy",
            database="healthy",
            service="test",
            version="test",
        )


class EndpointProtectionTests(unittest.TestCase):
    def setUp(self):
        self.service = EmptyOperationalService()
        for dependency in (
            get_incident_service,
            get_metric_service,
            get_schema_snapshot_service,
            get_dbt_metadata_service,
            get_pipeline_service,
        ):
            app.dependency_overrides[dependency] = lambda: self.service
        app.dependency_overrides[get_user_repository] = lambda: None
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()

    def test_every_operational_router_rejects_missing_token(self):
        for path in PROTECTED_PATHS:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(
                    response.json(),
                    {"detail": "Could not validate credentials"},
                )
        self.assertFalse(self.service.called)

    def test_malformed_and_expired_tokens_return_401(self):
        expired = create_access_token(
            subject=USER_ID,
            settings=make_settings(jwt_access_token_expire_minutes=1),
            now=datetime.now(timezone.utc) - timedelta(minutes=2),
        )
        for token in ("malformed", expired):
            with self.subTest(token=token[:10]):
                response = self.client.get(
                    "/api/v1/incidents",
                    headers={"Authorization": f"Bearer {token}"},
                )
                self.assertEqual(response.status_code, 401)
        self.assertFalse(self.service.called)

    def test_all_seeded_roles_access_every_operational_router(self):
        for role in ("Admin", "Operator", "ReadOnly"):
            app.dependency_overrides[get_current_active_user] = (
                lambda selected_role=role: active_user(selected_role)
            )
            for path in PROTECTED_PATHS:
                with self.subTest(role=role, path=path):
                    self.assertEqual(self.client.get(path).status_code, 200)

    def test_authenticated_query_validation_and_404_are_preserved(self):
        app.dependency_overrides[get_current_active_user] = (
            lambda: active_user("ReadOnly")
        )
        self.assertEqual(
            self.client.get("/api/v1/metrics?limit=0").status_code,
            422,
        )
        response = self.client.get(
            "/api/v1/incidents/"
            "11111111-1111-4111-8111-111111111111"
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Incident not found"})


class RoleDependencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_accepted_role_is_allowed(self):
        dependency = require_roles("Admin", "Operator")
        user = active_user("Operator")
        self.assertEqual(await dependency(user), user)

    async def test_roleless_or_unaccepted_user_receives_403(self):
        dependency = require_roles("Admin")
        for roles in ([], ["ReadOnly"]):
            user = active_user("ReadOnly").model_copy(
                update={"roles": roles}
            )
            with self.subTest(roles=roles):
                with self.assertRaises(HTTPException) as raised:
                    await dependency(user)
                self.assertEqual(raised.exception.status_code, 403)
                self.assertEqual(
                    raised.exception.detail,
                    "Insufficient permissions",
                )

    def test_required_roles_must_be_nonblank_and_declared(self):
        for roles in ((), ("",), ("Unknown",)):
            with self.subTest(roles=roles):
                with self.assertRaises(ValueError):
                    require_roles(*roles)

    async def test_role_change_changes_authorization_result(self):
        dependency = require_roles("Admin")
        user = active_user("ReadOnly")
        with self.assertRaises(HTTPException):
            await dependency(user)
        changed = user.model_copy(update={"roles": ["Admin"]})
        self.assertEqual(await dependency(changed), changed)


class PublicAndOpenApiTests(unittest.TestCase):
    def test_health_remains_public(self):
        app.dependency_overrides[get_health_service] = (
            lambda: StubHealthService()
        )
        client = TestClient(app)
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        app.dependency_overrides.clear()
        client.close()

    def test_openapi_secures_only_operational_routes(self):
        schema = create_app(make_settings()).openapi()
        for path in PROTECTED_PATHS:
            self.assertEqual(
                schema["paths"][path]["get"]["security"],
                [{"OAuth2PasswordBearer": []}],
            )
        self.assertNotIn("security", schema["paths"]["/health"]["get"])
        self.assertNotIn(
            "security",
            schema["paths"]["/api/v1/auth/token"]["post"],
        )

    def test_docs_setting_is_preserved(self):
        enabled = TestClient(create_app(make_settings(api_docs_enabled=True)))
        disabled = TestClient(
            create_app(make_settings(api_docs_enabled=False))
        )
        self.assertEqual(enabled.get("/docs").status_code, 200)
        self.assertEqual(disabled.get("/docs").status_code, 404)
        enabled.close()
        disabled.close()


if __name__ == "__main__":
    unittest.main()
