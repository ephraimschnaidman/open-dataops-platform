import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform"))

from api.config import Settings  # noqa: E402
from api.main import app  # noqa: E402
from api.repositories.health import HealthRepository  # noqa: E402
from api.routes.health import health  # noqa: E402
from api.schemas.health import HealthResponse  # noqa: E402
from api.services.health import HealthService  # noqa: E402


class StubHealthRepository:
    def __init__(self, result=True, error=None):
        self.result = result
        self.error = error

    async def database_is_healthy(self):
        if self.error:
            raise self.error
        return self.result


class StubResult:
    async def fetchone(self):
        return (1,)


class StubConnection:
    def __init__(self):
        self.query = None

    async def execute(self, query):
        self.query = query
        return StubResult()


class StubConnectionContext:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False


class StubPool:
    def __init__(self):
        self.connection_instance = StubConnection()

    def connection(self):
        return StubConnectionContext(self.connection_instance)


class ApiHealthTests(unittest.IsolatedAsyncioTestCase):
    async def test_repository_uses_lightweight_connectivity_query(self):
        pool = StubPool()

        is_healthy = await HealthRepository(pool).database_is_healthy()

        self.assertTrue(is_healthy)
        self.assertEqual(pool.connection_instance.query, "SELECT 1")

    async def test_healthy_response_matches_contract(self):
        service = HealthService(
            StubHealthRepository(),
            service_name="Open DataOps Platform API",
            version="0.1.0",
        )

        response = await health(service)

        self.assertEqual(
            response.model_dump(),
            {
                "status": "healthy",
                "database": "healthy",
                "service": "Open DataOps Platform API",
                "version": "0.1.0",
            },
        )

    async def test_database_failure_returns_safe_503(self):
        service = HealthService(
            StubHealthRepository(error=RuntimeError("secret connection detail")),
            service_name="Open DataOps Platform API",
            version="0.1.0",
        )

        with self.assertRaises(HTTPException) as raised:
            await health(service)

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.detail, "Database unavailable")
        self.assertNotIn("secret", str(raised.exception.detail))

    def test_health_response_rejects_invalid_status(self):
        with self.assertRaises(ValidationError):
            HealthResponse(
                status="degraded",
                database="healthy",
                service="Open DataOps Platform API",
                version="0.1.0",
            )

    def test_openapi_documents_health_contract(self):
        operation = app.openapi()["paths"]["/health"]["get"]

        self.assertEqual(
            operation["responses"]["200"]["content"]["application/json"]["schema"],
            {"$ref": "#/components/schemas/HealthResponse"},
        )
        self.assertIn("503", operation["responses"])

    def test_settings_follow_postgres_environment_pattern(self):
        environment = {
            "POSTGRES_HOST": "database.example",
            "POSTGRES_PORT": "5544",
            "POSTGRES_DB": "warehouse",
            "POSTGRES_USER": "reader",
            "POSTGRES_PASSWORD": "not-hard-coded",
            "API_JWT_SECRET_KEY": (
                "phase-2-test-secret-with-more-than-32-characters"
            ),
            "API_JWT_ISSUER": "test-issuer",
            "API_JWT_AUDIENCE": "test-audience",
            "AIRFLOW_API_URL": "https://airflow.example/api/v1",
            "AIRFLOW_API_USERNAME": "service-account",
            "AIRFLOW_API_PASSWORD": "not-hard-coded-either",
            "AIRFLOW_API_VERIFY_TLS": "true",
        }
        with patch.dict(os.environ, environment, clear=True):
            settings = Settings.from_environment()

        self.assertEqual(settings.postgres_host, "database.example")
        self.assertEqual(settings.postgres_port, 5544)
        self.assertEqual(settings.postgres_db, "warehouse")
        self.assertEqual(settings.postgres_user, "reader")
        self.assertEqual(settings.postgres_password, "not-hard-coded")
        self.assertEqual(str(settings.airflow_api_url), "https://airflow.example/api/v1")
        self.assertEqual(settings.airflow_api_username, "service-account")
        self.assertEqual(
            settings.airflow_api_password.get_secret_value(),
            "not-hard-coded-either",
        )
        self.assertTrue(settings.airflow_api_verify_tls)


if __name__ == "__main__":
    unittest.main()
