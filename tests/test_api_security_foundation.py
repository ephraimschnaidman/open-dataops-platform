import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

import jwt
from psycopg.errors import UniqueViolation
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from platform.api.cli.create_user import (  # noqa: E402
    DuplicateUsernameError,
    InvalidRoleError,
    ProvisioningError,
    normalize_and_validate_username,
    provision_user,
)
from platform.api.config import Settings  # noqa: E402
from platform.api.security import (  # noqa: E402
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
    verify_password_with_dummy_hash,
)

TEST_SECRET = "phase-2-test-secret-with-more-than-32-characters"
TEST_USER_ID = UUID("11111111-1111-4111-8111-111111111111")


def settings_data(**overrides):
    values = {
        "jwt_secret_key": TEST_SECRET,
        "jwt_issuer": "open-dataops-platform-api",
        "jwt_audience": "open-dataops-platform-clients",
    }
    values.update(overrides)
    return values


class SettingsTests(unittest.TestCase):
    def test_missing_jwt_secret_is_rejected(self):
        values = settings_data()
        del values["jwt_secret_key"]
        with self.assertRaises(ValidationError):
            Settings(**values)

    def test_weak_and_placeholder_jwt_secrets_are_rejected(self):
        for secret in (
            "short",
            "replace_with_at_least_32_random_characters",
            "change_this_secret_to_a_long_random_value",
        ):
            with self.subTest(secret=secret):
                with self.assertRaises(ValidationError):
                    Settings(**settings_data(jwt_secret_key=secret))

    def test_invalid_expiration_is_rejected(self):
        for minutes in (0, 1441):
            with self.subTest(minutes=minutes):
                with self.assertRaises(ValidationError):
                    Settings(
                        **settings_data(
                            jwt_access_token_expire_minutes=minutes
                        )
                    )

    def test_pool_min_must_not_exceed_max(self):
        with self.assertRaises(ValidationError):
            Settings(
                **settings_data(
                    database_pool_min_size=6,
                    database_pool_max_size=5,
                )
            )

    def test_docs_boolean_environment_parsing(self):
        base_environment = {
            "API_JWT_SECRET_KEY": TEST_SECRET,
            "API_JWT_ISSUER": "issuer",
            "API_JWT_AUDIENCE": "audience",
        }
        for value, expected in (
            ("true", True),
            ("YES", True),
            ("1", True),
            ("on", True),
            ("false", False),
            ("NO", False),
            ("0", False),
            ("off", False),
        ):
            with self.subTest(value=value):
                environment = {
                    **base_environment,
                    "API_DOCS_ENABLED": value,
                }
                with patch.dict(os.environ, environment, clear=True):
                    self.assertEqual(
                        Settings.from_environment().api_docs_enabled,
                        expected,
                    )

        with patch.dict(
            os.environ,
            {**base_environment, "API_DOCS_ENABLED": "sometimes"},
            clear=True,
        ):
            with self.assertRaises(ValueError):
                Settings.from_environment()


class PasswordAndJwtTests(unittest.TestCase):
    def test_argon2_hashing_and_verification(self):
        plaintext = "correct horse battery staple"
        encoded = hash_password(plaintext)
        self.assertNotEqual(encoded, plaintext)
        self.assertTrue(encoded.startswith("$argon2"))
        self.assertTrue(verify_password(plaintext, encoded))
        self.assertFalse(verify_password("incorrect", encoded))

    def test_dummy_hash_verification_does_not_authenticate(self):
        self.assertFalse(verify_password_with_dummy_hash("unknown password"))

    def test_valid_jwt_creation_and_decoding(self):
        settings = Settings(**settings_data())
        token = create_access_token(subject=TEST_USER_ID, settings=settings)
        claims = decode_access_token(token, settings=settings)
        self.assertEqual(claims["sub"], str(TEST_USER_ID))
        self.assertEqual(claims["iss"], settings.jwt_issuer)
        self.assertEqual(claims["aud"], settings.jwt_audience)
        UUID(claims["jti"])

    def test_expired_jwt_is_rejected(self):
        settings = Settings(
            **settings_data(jwt_access_token_expire_minutes=1)
        )
        token = create_access_token(
            subject=TEST_USER_ID,
            settings=settings,
            now=datetime.now(timezone.utc) - timedelta(minutes=2),
        )
        with self.assertRaises(jwt.ExpiredSignatureError):
            decode_access_token(token, settings=settings)

    def test_invalid_signature_is_rejected(self):
        issuer = Settings(**settings_data())
        verifier = Settings(
            **settings_data(
                jwt_secret_key=(
                    "a-different-test-secret-with-more-than-32-characters"
                )
            )
        )
        token = create_access_token(subject=TEST_USER_ID, settings=issuer)
        with self.assertRaises(jwt.InvalidSignatureError):
            decode_access_token(token, settings=verifier)

    def test_wrong_issuer_and_audience_are_rejected(self):
        issuer = Settings(**settings_data())
        token = create_access_token(subject=TEST_USER_ID, settings=issuer)
        with self.assertRaises(jwt.InvalidIssuerError):
            decode_access_token(
                token,
                settings=Settings(**settings_data(jwt_issuer="wrong")),
            )
        with self.assertRaises(jwt.InvalidAudienceError):
            decode_access_token(
                token,
                settings=Settings(**settings_data(jwt_audience="wrong")),
            )

    def test_missing_required_claim_is_rejected(self):
        settings = Settings(**settings_data())
        now = datetime.now(timezone.utc)
        token = jwt.encode(
            {
                "sub": str(TEST_USER_ID),
                "iss": settings.jwt_issuer,
                "aud": settings.jwt_audience,
                "iat": now,
                "nbf": now,
                "exp": now + timedelta(minutes=30),
            },
            settings.jwt_secret_key,
            algorithm="HS256",
        )
        with self.assertRaises(jwt.MissingRequiredClaimError):
            decode_access_token(token, settings=settings)


class FakeTransaction:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        self.connection.transaction_started = True
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.connection.rolled_back = exc_type is not None
        self.connection.committed = exc_type is None
        return False


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.last_query = ""
        self.insert_parameters = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query, parameters):
        self.last_query = query
        if "FROM security.roles" in query:
            self.connection.requested_roles = parameters[0]
        elif "INSERT INTO security.users" in query:
            if self.connection.duplicate_username:
                raise UniqueViolation("duplicate username")
            self.insert_parameters = parameters
            self.connection.insert_parameters = parameters

    def fetchall(self):
        return self.connection.roles

    def fetchone(self):
        return (TEST_USER_ID,)

    def executemany(self, query, parameters):
        self.connection.role_assignments = parameters


class FakeConnection:
    def __init__(self, roles, *, duplicate_username=False):
        self.roles = roles
        self.duplicate_username = duplicate_username
        self.transaction_started = False
        self.committed = False
        self.rolled_back = False
        self.insert_parameters = None
        self.role_assignments = None

    def transaction(self):
        return FakeTransaction(self)

    def cursor(self):
        return FakeCursor(self)


class ProvisioningTests(unittest.TestCase):
    def test_username_is_normalized_and_validated(self):
        self.assertEqual(
            normalize_and_validate_username("  Valid.User-1  "),
            "valid.user-1",
        )
        for username in ("ab", "_invalid", "has space", "UP"):
            with self.subTest(username=username):
                with self.assertRaises(ProvisioningError):
                    normalize_and_validate_username(username)

    def test_plaintext_is_not_stored_and_roles_are_assigned(self):
        connection = FakeConnection([(1, "Admin"), (3, "ReadOnly")])
        plaintext = "never store this plaintext"
        provision_user(
            connection,
            username="Test.User",
            plaintext_password=plaintext,
            role_names=["Admin", "ReadOnly"],
        )
        self.assertTrue(connection.committed)
        self.assertFalse(connection.rolled_back)
        self.assertEqual(connection.insert_parameters[0], "test.user")
        self.assertNotEqual(connection.insert_parameters[1], plaintext)
        self.assertTrue(connection.insert_parameters[1].startswith("$argon2"))
        self.assertEqual(
            connection.role_assignments,
            [(TEST_USER_ID, 1), (TEST_USER_ID, 3)],
        )

    def test_invalid_role_rolls_back_transaction(self):
        connection = FakeConnection([(1, "Admin")])
        with self.assertRaises(InvalidRoleError):
            provision_user(
                connection,
                username="test.user",
                plaintext_password="secret",
                role_names=["Admin", "Missing"],
            )
        self.assertTrue(connection.transaction_started)
        self.assertTrue(connection.rolled_back)
        self.assertFalse(connection.committed)
        self.assertIsNone(connection.insert_parameters)

    def test_duplicate_username_is_safe_and_rolls_back(self):
        connection = FakeConnection(
            [(1, "Admin")],
            duplicate_username=True,
        )
        with self.assertRaises(DuplicateUsernameError) as raised:
            provision_user(
                connection,
                username="test.user",
                plaintext_password="secret",
                role_names=["Admin"],
            )
        self.assertNotIn("secret", str(raised.exception))
        self.assertTrue(connection.rolled_back)
        self.assertFalse(connection.committed)


class MigrationSqlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        migration_path = (
            Path(__file__).resolve().parents[1]
            / "platform"
            / "warehouse"
            / "init"
            / "10_create_security_tables.sql"
        )
        cls.sql = migration_path.read_text(encoding="utf-8")

    def test_schema_tables_constraints_and_index_are_declared(self):
        for fragment in (
            "CREATE SCHEMA IF NOT EXISTS security",
            "CREATE TABLE IF NOT EXISTS security.users",
            "CREATE TABLE IF NOT EXISTS security.roles",
            "CREATE TABLE IF NOT EXISTS security.user_roles",
            "username = lower(username)",
            "ON DELETE CASCADE",
            "ON DELETE RESTRICT",
            "ON security.user_roles (role_id, user_id)",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.sql)

    def test_migration_is_transactional_concurrency_safe_and_repeatable(self):
        self.assertIn("BEGIN;", self.sql)
        self.assertIn("COMMIT;", self.sql)
        self.assertIn("pg_advisory_xact_lock", self.sql)
        self.assertIn("IF NOT EXISTS", self.sql)
        self.assertIn("ON CONFLICT (name) DO UPDATE", self.sql)

    def test_exact_roles_are_seeded_without_grafana_grants(self):
        for role in ("Admin", "Operator", "ReadOnly"):
            self.assertIn(f"('{role}',", self.sql)
        self.assertNotIn("grafana_reader", self.sql)
        self.assertNotIn("GRANT", self.sql.upper())


if __name__ == "__main__":
    unittest.main()
