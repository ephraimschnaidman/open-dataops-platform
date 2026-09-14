import os
import sys
import unittest
import asyncio
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform"))

from api.auth_dependencies import get_current_active_user  # noqa: E402
from api.config import Settings  # noqa: E402
from api.main import create_app  # noqa: E402
from tests.test_api_authorization import active_user  # noqa: E402

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@unittest.skipUnless(
    os.getenv("RUN_SETTINGS_DB_INTEGRATION") == "1",
    "Set RUN_SETTINGS_DB_INTEGRATION=1 to run Settings PostgreSQL path tests",
)
class SettingsDatabaseIntegrationTests(unittest.TestCase):
    def test_write_read_validation_and_environment_invariants(self):
        application = create_app(Settings.from_environment())
        application.dependency_overrides[get_current_active_user] = lambda: active_user("Admin")
        environment_key = f"settings-qa-{uuid4().hex[:8]}"

        with TestClient(application) as client:
            original = client.get("/api/v1/settings").json()
            original_general = {
                "workspace_name": original["general"]["workspace_name"],
                "default_environment": original["general"]["default_environment"],
                "timezone": original["general"]["timezone"],
            }
            try:
                notifications = {**original["notifications"], "recipients": [*original["notifications"]["recipients"], "persistence-test@example.com"]}
                self.assertEqual(client.put("/api/v1/settings/notifications", json=notifications).status_code, 200)
                reloaded = client.get("/api/v1/settings").json()
                self.assertIn("persistence-test@example.com", reloaded["notifications"]["recipients"])

                defaults = {**original["operational_defaults"], "runtime_warning": 35}
                self.assertEqual(client.put("/api/v1/settings/operational-defaults", json=defaults).status_code, 200)
                self.assertEqual(client.get("/api/v1/settings").json()["operational_defaults"]["runtime_warning"], "35.00")
                invalid = {**defaults, "pipeline": {**defaults["pipeline"], "healthy": 101}}
                self.assertEqual(client.put("/api/v1/settings/operational-defaults", json=invalid).status_code, 422)
                self.assertEqual(client.get("/api/v1/settings").json()["operational_defaults"]["pipeline"]["healthy"], original["operational_defaults"]["pipeline"]["healthy"])

                created = client.post("/api/v1/settings/environments", json={"environment_key": environment_key, "name": f"Settings QA {environment_key[-8:]}", "description": "Temporary integrity test"})
                self.assertEqual(created.status_code, 201)
                make_default = {**original_general, "default_environment": environment_key}
                self.assertEqual(client.put("/api/v1/settings/general", json=make_default).status_code, 200)
                blocked_default = client.delete(f"/api/v1/settings/environments/{environment_key}")
                self.assertEqual((blocked_default.status_code, blocked_default.json()["code"]), (409, "DEFAULT_ENVIRONMENT_REQUIRED"))

                production = {**original_general, "default_environment": "production"}
                self.assertEqual(client.put("/api/v1/settings/general", json=production).status_code, 200)
                in_use = client.delete("/api/v1/settings/environments/development")
                self.assertEqual((in_use.status_code, in_use.json()["code"]), (409, "ENVIRONMENT_IN_USE"))
                self.assertEqual(client.delete(f"/api/v1/settings/environments/{environment_key}").status_code, 204)
            finally:
                client.put("/api/v1/settings/general", json=original_general)
                client.put("/api/v1/settings/notifications", json=original["notifications"])
                client.put("/api/v1/settings/operational-defaults", json=original["operational_defaults"])
                client.delete(f"/api/v1/settings/environments/{environment_key}")


if __name__ == "__main__":
    unittest.main()
