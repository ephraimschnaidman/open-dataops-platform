from __future__ import annotations

import argparse
import getpass
import sys
from collections.abc import Sequence
from typing import Any

import psycopg

from ..config import Settings, get_settings
from ..security import hash_password, normalize_and_validate_username


class PasswordRotationError(RuntimeError):
    pass


class UserNotFoundError(PasswordRotationError):
    pass


def rotate_password(
    connection: Any,
    *,
    username: str,
    plaintext_password: str,
) -> None:
    try:
        normalized_username = normalize_and_validate_username(username)
    except ValueError as error:
        raise PasswordRotationError(str(error)) from error
    if not plaintext_password:
        raise PasswordRotationError("Password must not be blank")

    encoded_password = hash_password(plaintext_password)
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE security.users
                SET password_hash = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE username = %s
                RETURNING user_id
                """,
                (encoded_password, normalized_username),
            )
            if cursor.fetchone() is None:
                raise UserNotFoundError("Configured API user does not exist")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Securely rotate an existing Platform API user password."
    )
    parser.add_argument("username", help="Existing username to update")
    return parser


def run(arguments: Sequence[str] | None = None) -> int:
    parsed = build_parser().parse_args(arguments)
    try:
        password = getpass.getpass("New password: ")
        confirmation = getpass.getpass("Confirm new password: ")
        if password != confirmation:
            raise PasswordRotationError("Passwords do not match")
        settings: Settings = get_settings()
        with psycopg.connect(
            **settings.database_connection_kwargs()
        ) as connection:
            rotate_password(
                connection,
                username=parsed.username,
                plaintext_password=password,
            )
    except (EOFError, KeyboardInterrupt):
        print("Password rotation cancelled", file=sys.stderr)
        return 1
    except (PasswordRotationError, psycopg.Error, ValueError) as error:
        print(f"Password rotation failed: {error}", file=sys.stderr)
        return 1

    print("Password rotated for the requested API user")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
