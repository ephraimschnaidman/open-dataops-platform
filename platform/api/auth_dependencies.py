from __future__ import annotations

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from api.config import Settings, get_settings
from api.repositories.users import UserRepository
from api.schemas.auth import CurrentUser
from api.security import decode_access_token

DECLARED_ROLES = frozenset({"Admin", "Operator", "ReadOnly"})

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token",
    auto_error=False,
)


def credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_user_repository(request: Request) -> UserRepository:
    return UserRepository(request.app.state.database_pool)


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    repository: Annotated[UserRepository, Depends(get_user_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CurrentUser:
    if token is None:
        raise credentials_exception()
    try:
        claims = decode_access_token(token, settings=settings)
        user_id = UUID(claims["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        raise credentials_exception() from None

    try:
        user = await repository.get_by_user_id(user_id)
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from error
    if user is None:
        raise credentials_exception()

    return CurrentUser(
        user_id=user.user_id,
        username=user.username,
        is_active=user.is_active,
        roles=user.roles,
    )


async def get_current_active_user(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    if not current_user.is_active:
        raise credentials_exception()
    return current_user


def require_roles(*allowed_roles: str):
    if not allowed_roles:
        raise ValueError("At least one required role must be declared")
    normalized_roles = tuple(role.strip() for role in allowed_roles)
    if any(not role for role in normalized_roles):
        raise ValueError("Required role names must be nonblank")
    unknown_roles = sorted(set(normalized_roles) - DECLARED_ROLES)
    if unknown_roles:
        raise ValueError(
            f"Unknown required role name(s): {', '.join(unknown_roles)}"
        )
    allowed_role_set = frozenset(normalized_roles)

    async def enforce_required_roles(
        current_user: Annotated[
            CurrentUser,
            Depends(get_current_active_user),
        ],
    ) -> CurrentUser:
        if allowed_role_set.isdisjoint(current_user.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return enforce_required_roles
