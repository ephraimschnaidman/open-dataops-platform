from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
from typing import Any
from uuid import UUID, uuid4

import jwt
from pwdlib import PasswordHash

from .config import JWT_ALGORITHM, Settings

JWT_CLOCK_SKEW_LEEWAY_SECONDS = 30
JWT_REQUIRED_CLAIMS = ("sub", "iss", "aud", "iat", "nbf", "exp", "jti")
USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")

password_hash = PasswordHash.recommended()
_DUMMY_PASSWORD_HASH = password_hash.hash(
    "open-dataops-dummy-password-verification-value"
)


def normalize_and_validate_username(username: str) -> str:
    normalized = username.strip().lower()
    if not USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError(
            "Username must be 3-64 characters and contain only lowercase "
            "letters, numbers, dots, underscores, or hyphens"
        )
    return normalized


def hash_password(plaintext_password: str) -> str:
    return password_hash.hash(plaintext_password)


def verify_password(plaintext_password: str, encoded_hash: str) -> bool:
    return password_hash.verify(plaintext_password, encoded_hash)


def verify_password_with_dummy_hash(plaintext_password: str) -> bool:
    return verify_password(plaintext_password, _DUMMY_PASSWORD_HASH)


def create_access_token(
    *,
    subject: UUID,
    settings: Settings,
    now: datetime | None = None,
) -> str:
    issued_at = now or datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    claims = {
        "sub": str(subject),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": issued_at,
        "nbf": issued_at,
        "exp": expires_at,
        "jti": str(uuid4()),
    }
    return jwt.encode(
        claims,
        settings.jwt_secret_key,
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str, *, settings: Settings) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[JWT_ALGORITHM],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
        leeway=JWT_CLOCK_SKEW_LEEWAY_SECONDS,
        options={"require": list(JWT_REQUIRED_CLAIMS)},
    )
