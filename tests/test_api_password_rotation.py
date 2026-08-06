from __future__ import annotations

import unittest
from unittest.mock import patch
from uuid import UUID

from platform.api.cli.rotate_password import (
    PasswordRotationError,
    UserNotFoundError,
    rotate_password,
)


USER_ID = UUID("11111111-1111-4111-8111-111111111111")


class FakeTransaction:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.connection.committed = exc_type is None
        self.connection.rolled_back = exc_type is not None
        return False


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query, parameters):
        self.connection.query = query
        self.connection.parameters = parameters

    def fetchone(self):
        return (USER_ID,) if self.connection.user_exists else None


class FakeConnection:
    def __init__(self, *, user_exists=True):
        self.user_exists = user_exists
        self.committed = False
        self.rolled_back = False
        self.query = ""
        self.parameters = None

    def transaction(self):
        return FakeTransaction(self)

    def cursor(self):
        return FakeCursor(self)


class PasswordRotationTests(unittest.TestCase):
    @patch(
        "platform.api.cli.rotate_password.hash_password",
        return_value="$argon2id$rotated-hash",
    )
    def test_rotates_only_password_for_normalized_existing_user(self, hasher):
        connection = FakeConnection()
        plaintext = "never-persist-this-value"

        rotate_password(
            connection,
            username="  Validation.User  ",
            plaintext_password=plaintext,
        )

        hasher.assert_called_once_with(plaintext)
        self.assertTrue(connection.committed)
        self.assertFalse(connection.rolled_back)
        self.assertEqual(
            connection.parameters,
            ("$argon2id$rotated-hash", "validation.user"),
        )
        self.assertNotIn(plaintext, str(connection.parameters))
        self.assertNotIn("is_active", connection.query.lower())
        self.assertNotIn("user_roles", connection.query.lower())

    def test_missing_user_rolls_back_without_creating_one(self):
        connection = FakeConnection(user_exists=False)
        with self.assertRaises(UserNotFoundError):
            rotate_password(
                connection,
                username="validation.user",
                plaintext_password="secret",
            )
        self.assertTrue(connection.rolled_back)
        self.assertFalse(connection.committed)
        self.assertNotIn("insert", connection.query.lower())

    def test_blank_password_and_invalid_username_are_rejected(self):
        with self.assertRaises(PasswordRotationError):
            rotate_password(
                FakeConnection(), username="valid.user", plaintext_password=""
            )
        with self.assertRaises(PasswordRotationError):
            rotate_password(
                FakeConnection(), username="INVALID USER", plaintext_password="x"
            )


if __name__ == "__main__":
    unittest.main()
