from __future__ import annotations

import argparse
import getpass
import sys
from collections.abc import Sequence
from typing import Any

import psycopg
from psycopg import sql
from psycopg.errors import UniqueViolation

from ..config import Settings, get_settings
from ..security import (
    hash_password,
    normalize_and_validate_username as normalize_security_username,
)


class ProvisioningError(RuntimeError):
    pass


class DuplicateUsernameError(ProvisioningError):
    pass


class InvalidRoleError(ProvisioningError):
    pass


def normalize_and_validate_username(username: str) -> str:
    try:
        return normalize_security_username(username)
    except ValueError as error:
        raise ProvisioningError(str(error)) from error


def prompt_for_password() -> str:
    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise ProvisioningError("Passwords do not match")
    if not password:
        raise ProvisioningError("Password must not be blank")
    return password


def provision_user(
    connection: Any,
    *,
    username: str,
    plaintext_password: str,
    role_names: Sequence[str],
) -> None:
    normalized_username = normalize_and_validate_username(username)
    requested_roles = list(dict.fromkeys(role_names))
    if not requested_roles:
        raise InvalidRoleError("At least one role is required")

    encoded_password = hash_password(plaintext_password)
    try:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT role_id, name
                    FROM security.roles
                    WHERE name = ANY(%s)
                    """,
                    (requested_roles,),
                )
                roles = cursor.fetchall()
                found_names = {row[1] for row in roles}
                missing_names = sorted(set(requested_roles) - found_names)
                if missing_names:
                    raise InvalidRoleError(
                        f"Unknown role name(s): {', '.join(missing_names)}"
                    )

                cursor.execute(
                    """
                    INSERT INTO security.users (username, password_hash)
                    VALUES (%s, %s)
                    RETURNING user_id
                    """,
                    (normalized_username, encoded_password),
                )
                user_id = cursor.fetchone()[0]
                cursor.executemany(
                    """
                    INSERT INTO security.user_roles (user_id, role_id)
                    VALUES (%s, %s)
                    """,
                    [(user_id, role_id) for role_id, _ in roles],
                )
    except UniqueViolation as error:
        raise DuplicateUsernameError(
            f"User '{normalized_username}' already exists"
        ) from error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Securely provision a Platform API user."
    )
    parser.add_argument("username", help="Username to create")
    parser.add_argument(
        "--role",
        dest="roles",
        action="append",
        required=True,
        help="Role to assign; repeat for multiple roles",
    )
    return parser


def run(arguments: Sequence[str] | None = None) -> int:
    parsed = build_parser().parse_args(arguments)
    try:
        username = normalize_and_validate_username(parsed.username)
        plaintext_password = prompt_for_password()
        settings: Settings = get_settings()
        with psycopg.connect(**settings.database_connection_kwargs()) as connection:
            provision_user(
                connection,
                username=username,
                plaintext_password=plaintext_password,
                role_names=parsed.roles,
            )
    except (EOFError, KeyboardInterrupt):
        print("User provisioning cancelled", file=sys.stderr)
        return 1
    except (ProvisioningError, psycopg.Error, ValueError) as error:
        print(f"User provisioning failed: {error}", file=sys.stderr)
        return 1

    print(f"Created user '{username}' with role(s): {', '.join(parsed.roles)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
