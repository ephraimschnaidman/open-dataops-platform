import sys
import unittest
from copy import deepcopy
from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform"))

from api.auth_dependencies import get_current_active_user  # noqa: E402
from api.main import app  # noqa: E402
from api.routes.settings import get_settings_service  # noqa: E402
from api.schemas.settings import OperationalDefaults, SettingsResponse  # noqa: E402
from api.services.settings import (  # noqa: E402
    DefaultEnvironmentRequiredError, EnvironmentInUseError,
    EnvironmentNotFoundError, SettingsService,
)
from tests.api_auth_test_helpers import ACTIVE_TEST_USER  # noqa: E402
from tests.test_api_authorization import active_user  # noqa: E402


def settings_value():
    return {
        "general": {"workspace_name": "Corvetra Demo Workspace", "workspace_id": "workspace_01J4X8K97B", "default_environment": "production", "timezone": "America/New_York", "date_time_display": "LOCAL_WORKSPACE_TIME"},
        "environments": [
            {"environment_key": "production", "name": "Production", "description": None, "status": "ACTIVE", "resources": 1, "pipelines": 1, "sources": 0, "other": 0, "created_at": "2025-01-12", "is_default": True},
            {"environment_key": "qa", "name": "QA", "description": None, "status": "ACTIVE", "resources": 0, "pipelines": 0, "sources": 0, "other": 0, "created_at": "2026-08-11", "is_default": False},
        ],
        "notifications": {"enabled": True, "recipients": ["ops@example.com"], "severity": "CRITICAL_AND_WARNING", "notify_resolved": True},
        "operational_defaults": {
            "pipeline": {"healthy": 98, "warning": 95}, "schedule": {"healthy": 99, "warning": 95}, "source": {"healthy": 99.5, "warning": 98},
            "runtime_warning": 30, "freshness_hours": 2, "validation_severity": "WARNING", "blocking_alerts": True, "warning_alerts": False,
        },
    }


class StubSettingsService:
    def __init__(self):
        self.value = SettingsResponse.model_validate(settings_value())
        self.notification_updates = []
        self.default_updates = []
        self.delete_error = None
        self.deleted = []

    async def get_settings(self):
        return self.value

    async def update_notifications(self, value):
        self.notification_updates.append(value)
        return value

    async def update_operational_defaults(self, value):
        self.value.operational_defaults = value
        return value

    async def update_general(self, value):
        self.default_updates.append(value.default_environment)
        data = settings_value()
        data["general"]["default_environment"] = value.default_environment
        for environment in data["environments"]:
            environment["is_default"] = environment["environment_key"] == value.default_environment
        self.value = SettingsResponse.model_validate(data)
        return self.value

    async def create_environment(self, value):
        return self.value

    async def delete_environment(self, key):
        if self.delete_error:
            raise self.delete_error
        self.deleted.append(key)


class SettingsApiTests(unittest.TestCase):
    def setUp(self):
        self.service = StubSettingsService()
        app.dependency_overrides[get_settings_service] = lambda: self.service
        app.dependency_overrides[get_current_active_user] = lambda: active_user("Admin")
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()

    def defaults_payload(self, **overrides):
        value = deepcopy(settings_value()["operational_defaults"])
        value.update(overrides)
        return value

    def test_notification_write_returns_only_after_service_success(self):
        payload = {"enabled": True, "recipients": ["owner@example.com"], "severity": "CRITICAL_ONLY", "notify_resolved": False}
        response = self.client.put("/api/v1/settings/notifications", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), payload)
        self.assertEqual(len(self.service.notification_updates), 1)

    def test_percentage_101_is_rejected_before_service(self):
        payload = self.defaults_payload(pipeline={"healthy": 101, "warning": 95})
        response = self.client.put("/api/v1/settings/operational-defaults", json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.service.value.operational_defaults.runtime_warning, 30)
        with self.assertRaises(ValidationError):
            OperationalDefaults.model_validate(payload)

    def test_valid_operational_default_and_default_environment_updates(self):
        payload = self.defaults_payload(runtime_warning=35)
        self.assertEqual(self.client.put("/api/v1/settings/operational-defaults", json=payload).status_code, 200)
        self.assertEqual(self.service.value.operational_defaults.runtime_warning, 35)
        general = {"workspace_name": "Corvetra Demo Workspace", "default_environment": "qa", "timezone": "America/New_York"}
        response = self.client.put("/api/v1/settings/general", json=general)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["general"]["default_environment"], "qa")

    def test_default_and_in_use_delete_errors_and_empty_delete_success(self):
        cases = (
            (DefaultEnvironmentRequiredError(), "DEFAULT_ENVIRONMENT_REQUIRED"),
            (EnvironmentInUseError(), "ENVIRONMENT_IN_USE"),
            (EnvironmentNotFoundError(), "ENVIRONMENT_NOT_FOUND"),
        )
        for error, code in cases:
            with self.subTest(code=code):
                self.service.delete_error = error
                response = self.client.delete("/api/v1/settings/environments/qa")
                self.assertIn(response.status_code, (404, 409))
                self.assertEqual(response.json()["code"], code)
        self.service.delete_error = None
        response = self.client.delete("/api/v1/settings/environments/qa")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.service.deleted, ["qa"])

    def test_read_allows_readonly_but_writes_require_admin(self):
        app.dependency_overrides[get_current_active_user] = lambda: active_user("ReadOnly")
        self.assertEqual(self.client.get("/api/v1/settings").status_code, 200)
        response = self.client.put("/api/v1/settings/notifications", json={"enabled": False, "recipients": [], "severity": "CRITICAL_ONLY", "notify_resolved": False})
        self.assertEqual(response.status_code, 403)


class SettingsServiceInvariantTests(unittest.IsolatedAsyncioTestCase):
    async def test_repository_outcomes_are_independent_stable_invariants(self):
        class Repository:
            def __init__(self, outcome): self.outcome = outcome
            async def delete_environment(self, _key): return self.outcome

        for outcome, error in (("DEFAULT", DefaultEnvironmentRequiredError), ("IN_USE", EnvironmentInUseError), ("NOT_FOUND", EnvironmentNotFoundError)):
            with self.subTest(outcome=outcome):
                with self.assertRaises(error):
                    await SettingsService(Repository(outcome)).delete_environment("qa")
        await SettingsService(Repository("DELETED")).delete_environment("qa")


if __name__ == "__main__":
    unittest.main()
