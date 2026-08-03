import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

import jwt
from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform"))

from api.auth_dependencies import (  # noqa: E402
    get_current_active_user,
    get_current_user,
)
from api.config import Settings  # noqa: E402
from api.main import app, create_app  # noqa: E402
from api.routes.auth import get_authentication_service  # noqa: E402
from api.schemas.auth import CurrentUser, RepositoryUser, TokenResponse  # noqa: E402
from api.security import create_access_token, hash_password  # noqa: E402
from api.services.authentication import (  # noqa: E402
    AuthenticationService,
    InvalidCredentialsError,
)

TEST_SECRET = "phase-3-test-secret-with-more-than-32-characters"
USER_ID = UUID("11111111-1111-4111-8111-111111111111")


def make_settings(**overrides):
    values = {
        "jwt_secret_key": TEST_SECRET,
        "jwt_issuer": "open-dataops-platform-api",
        "jwt_audience": "open-dataops-platform-clients",
        "api_docs_enabled": True,
        "airflow_api_url": "http://airflow.test/api/v1",
        "airflow_api_username": "test-user",
        "airflow_api_password": "test-password",
        "airflow_api_verify_tls": True,
    }
    values.update(overrides)
    return Settings(**values)


def make_user(**overrides):
    values = {
        "user_id": USER_ID,
        "username": "test.user",
        "password_hash": hash_password("correct-password"),
        "is_active": True,
        "roles": ["Operator"],
    }
    values.update(overrides)
    return RepositoryUser(**values)


class StubUserRepository:
    def __init__(self, user=None):
        self.user = user
        self.error = None
        self.username = None
        self.user_id = None
        self.last_login_user_id = None

    async def get_by_username(self, username):
        self.username = username
        if self.error:
            raise self.error
        return self.user

    async def get_by_user_id(self, user_id):
        self.user_id = user_id
        if self.error:
            raise self.error
        return self.user

    async def update_last_login_at(self, user_id):
        if self.error:
            raise self.error
        self.last_login_user_id = user_id


class AuthenticationServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_success_normalizes_username_and_updates_last_login(self):
        repository = StubUserRepository(make_user())
        result = await AuthenticationService(
            repository,
            make_settings(jwt_access_token_expire_minutes=45),
        ).authenticate(
            username="  Test.User  ",
            password="correct-password",
        )
        self.assertEqual(repository.username, "test.user")
        self.assertEqual(repository.last_login_user_id, USER_ID)
        self.assertEqual(result.token_type, "bearer")
        self.assertEqual(result.expires_in, 2700)
        self.assertNotIn("password_hash", result.model_dump())

    async def test_unknown_username_uses_dummy_verification(self):
        repository = StubUserRepository()
        with patch(
            "api.services.authentication.verify_password_with_dummy_hash"
        ) as dummy_verify:
            with self.assertRaises(InvalidCredentialsError):
                await AuthenticationService(
                    repository,
                    make_settings(),
                ).authenticate(
                    username="unknown.user",
                    password="submitted-password",
                )
        dummy_verify.assert_called_once_with("submitted-password")

    async def test_invalid_username_uses_dummy_verification(self):
        repository = StubUserRepository()
        with patch(
            "api.services.authentication.verify_password_with_dummy_hash"
        ) as dummy_verify:
            with self.assertRaises(InvalidCredentialsError):
                await AuthenticationService(
                    repository,
                    make_settings(),
                ).authenticate(username="!!", password="submitted")
        dummy_verify.assert_called_once_with("submitted")

    async def test_wrong_password_and_inactive_user_are_identical(self):
        cases = (
            (make_user(), "wrong-password"),
            (make_user(is_active=False), "correct-password"),
        )
        messages = []
        for user, password in cases:
            with self.subTest(active=user.is_active, password=password):
                with self.assertRaises(InvalidCredentialsError) as raised:
                    await AuthenticationService(
                        StubUserRepository(user),
                        make_settings(),
                    ).authenticate(
                        username=user.username,
                        password=password,
                    )
                messages.append(str(raised.exception))
        self.assertEqual(messages[0], messages[1])


class StubAuthenticationService:
    def __init__(self):
        self.error = None
        self.arguments = None

    async def authenticate(self, **arguments):
        self.arguments = arguments
        if self.error:
            raise self.error
        return TokenResponse(
            access_token="encoded-token",
            expires_in=1800,
        )


class AuthenticationRouteTests(unittest.TestCase):
    def setUp(self):
        self.service = StubAuthenticationService()
        app.dependency_overrides[get_authentication_service] = (
            lambda: self.service
        )
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()

    def test_successful_form_login_and_response_schema(self):
        response = self.client.post(
            "/api/v1/auth/token",
            data={"username": "test.user", "password": "secret"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "access_token": "encoded-token",
                "token_type": "bearer",
                "expires_in": 1800,
            },
        )
        self.assertEqual(
            self.service.arguments,
            {"username": "test.user", "password": "secret"},
        )

    def test_all_bad_logins_return_same_generic_401(self):
        self.service.error = InvalidCredentialsError()
        response = self.client.post(
            "/api/v1/auth/token",
            data={"username": "unknown", "password": "wrong"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(),
            {"detail": "Incorrect username or password"},
        )
        self.assertEqual(response.headers["www-authenticate"], "Bearer")

    def test_database_error_is_safe_503(self):
        self.service.error = RuntimeError(
            "postgresql://user:password@database SELECT password_hash"
        )
        with self.assertLogs("api.routes.auth", level="WARNING") as logs:
            response = self.client.post(
                "/api/v1/auth/token",
                data={"username": "test.user", "password": "secret"},
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Database unavailable"})
        self.assertNotIn("password", response.text)
        self.assertNotIn("postgresql", " ".join(logs.output))


class CurrentUserDependencyTests(unittest.IsolatedAsyncioTestCase):
    async def assert_invalid_token(self, token):
        with self.assertRaises(HTTPException) as raised:
            await get_current_user(
                token=token,
                repository=StubUserRepository(make_user()),
                settings=make_settings(),
            )
        self.assertEqual(raised.exception.status_code, 401)
        self.assertEqual(
            raised.exception.detail,
            "Could not validate credentials",
        )
        self.assertEqual(
            raised.exception.headers,
            {"WWW-Authenticate": "Bearer"},
        )

    async def test_valid_token_loads_database_user_and_roles(self):
        repository = StubUserRepository(make_user(roles=["Admin", "Operator"]))
        token = create_access_token(subject=USER_ID, settings=make_settings())
        current_user = await get_current_user(
            token=token,
            repository=repository,
            settings=make_settings(),
        )
        self.assertEqual(current_user.user_id, USER_ID)
        self.assertEqual(current_user.roles, ["Admin", "Operator"])
        self.assertFalse(hasattr(current_user, "password_hash"))

    async def test_missing_and_malformed_tokens_are_rejected(self):
        for token in (None, "not-a-jwt"):
            with self.subTest(token=token):
                await self.assert_invalid_token(token)

    async def test_invalid_signature_is_rejected(self):
        token = create_access_token(
            subject=USER_ID,
            settings=make_settings(
                jwt_secret_key=(
                    "different-phase-3-secret-with-more-than-32-characters"
                )
            ),
        )
        await self.assert_invalid_token(token)

    async def test_expired_token_is_rejected(self):
        token = create_access_token(
            subject=USER_ID,
            settings=make_settings(jwt_access_token_expire_minutes=1),
            now=datetime.now(timezone.utc) - timedelta(minutes=2),
        )
        await self.assert_invalid_token(token)

    async def test_wrong_issuer_and_audience_are_rejected(self):
        for override in (
            {"jwt_issuer": "wrong-issuer"},
            {"jwt_audience": "wrong-audience"},
        ):
            token = create_access_token(
                subject=USER_ID,
                settings=make_settings(**override),
            )
            with self.subTest(override=override):
                await self.assert_invalid_token(token)

    async def test_missing_claim_and_invalid_subject_are_rejected(self):
        settings = make_settings()
        now = datetime.now(timezone.utc)
        base_claims = {
            "sub": str(USER_ID),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(minutes=30),
            "jti": str(uuid4()),
        }
        cases = (
            {key: value for key, value in base_claims.items() if key != "jti"},
            {**base_claims, "sub": "not-a-uuid"},
        )
        for claims in cases:
            token = jwt.encode(
                claims,
                settings.jwt_secret_key,
                algorithm="HS256",
            )
            with self.subTest(claims=claims):
                await self.assert_invalid_token(token)

    async def test_deleted_user_is_rejected(self):
        token = create_access_token(subject=USER_ID, settings=make_settings())
        with self.assertRaises(HTTPException) as raised:
            await get_current_user(
                token=token,
                repository=StubUserRepository(),
                settings=make_settings(),
            )
        self.assertEqual(raised.exception.status_code, 401)

    async def test_inactive_current_user_is_rejected(self):
        with self.assertRaises(HTTPException) as raised:
            await get_current_active_user(
                CurrentUser(
                    user_id=USER_ID,
                    username="test.user",
                    is_active=False,
                    roles=["Operator"],
                )
            )
        self.assertEqual(raised.exception.status_code, 401)

    async def test_role_and_active_changes_are_database_authoritative(self):
        repository = StubUserRepository(make_user(roles=["ReadOnly"]))
        token = create_access_token(subject=USER_ID, settings=make_settings())
        first = await get_current_user(
            token=token,
            repository=repository,
            settings=make_settings(),
        )
        repository.user = make_user(is_active=False, roles=["Admin"])
        second = await get_current_user(
            token=token,
            repository=repository,
            settings=make_settings(),
        )
        self.assertEqual(first.roles, ["ReadOnly"])
        self.assertEqual(second.roles, ["Admin"])
        with self.assertRaises(HTTPException):
            await get_current_active_user(second)

    async def test_database_error_is_safe_503(self):
        repository = StubUserRepository()
        repository.error = RuntimeError("SELECT password_hash")
        token = create_access_token(subject=USER_ID, settings=make_settings())
        with self.assertRaises(HTTPException) as raised:
            await get_current_user(
                token=token,
                repository=repository,
                settings=make_settings(),
            )
        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.detail, "Database unavailable")


class DocumentationAndPublicEndpointTests(unittest.TestCase):
    def test_docs_enabled_and_oauth2_password_flow(self):
        application = create_app(make_settings(api_docs_enabled=True))
        client = TestClient(application)
        self.assertEqual(client.get("/docs").status_code, 200)
        self.assertEqual(client.get("/redoc").status_code, 200)
        schema_response = client.get("/openapi.json")
        self.assertEqual(schema_response.status_code, 200)
        scheme = schema_response.json()["components"]["securitySchemes"][
            "OAuth2PasswordBearer"
        ]
        self.assertEqual(
            scheme["flows"]["password"]["tokenUrl"],
            "/api/v1/auth/token",
        )
        client.close()

    def test_docs_disabled(self):
        application = create_app(make_settings(api_docs_enabled=False))
        client = TestClient(application)
        for path in ("/docs", "/redoc", "/openapi.json"):
            with self.subTest(path=path):
                self.assertEqual(client.get(path).status_code, 404)
        client.close()

    def test_openapi_security_requirements_match_phase_4_policy(self):
        schema = create_app(make_settings()).openapi()
        public_operations = (
            ("/health", "get"),
            ("/api/v1/auth/token", "post"),
        )
        protected_operations = (
            ("/api/v1/incidents", "get"),
            ("/api/v1/metrics", "get"),
            ("/api/v1/schema-snapshots", "get"),
            ("/api/v1/dbt-metadata", "get"),
            ("/api/v1/pipelines", "get"),
        )
        for path, method in public_operations:
            with self.subTest(path=path):
                self.assertNotIn(
                    "security",
                    schema["paths"][path][method],
                )
        for path, method in protected_operations:
            with self.subTest(path=path):
                self.assertEqual(
                    schema["paths"][path][method]["security"],
                    [{"OAuth2PasswordBearer": []}],
                )


if __name__ == "__main__":
    unittest.main()
