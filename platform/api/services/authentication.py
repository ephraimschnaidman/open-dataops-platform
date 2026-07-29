from __future__ import annotations

from pwdlib.exceptions import UnknownHashError

from api.config import Settings
from api.repositories.users import UserRepository
from api.schemas.auth import TokenResponse
from api.security import (
    create_access_token,
    normalize_and_validate_username,
    verify_password,
    verify_password_with_dummy_hash,
)


class InvalidCredentialsError(ValueError):
    pass


class AuthenticationService:
    def __init__(
        self,
        repository: UserRepository,
        settings: Settings,
    ) -> None:
        self._repository = repository
        self._settings = settings

    async def authenticate(
        self,
        *,
        username: str,
        password: str,
    ) -> TokenResponse:
        try:
            normalized_username = normalize_and_validate_username(username)
        except ValueError:
            verify_password_with_dummy_hash(password)
            raise InvalidCredentialsError from None

        user = await self._repository.get_by_username(normalized_username)
        if user is None:
            verify_password_with_dummy_hash(password)
            raise InvalidCredentialsError

        try:
            password_is_valid = verify_password(password, user.password_hash)
        except UnknownHashError:
            password_is_valid = False

        if not password_is_valid or not user.is_active:
            raise InvalidCredentialsError

        await self._repository.update_last_login_at(user.user_id)
        access_token = create_access_token(
            subject=user.user_id,
            settings=self._settings,
        )
        return TokenResponse(
            access_token=access_token,
            expires_in=self._settings.jwt_access_token_expire_minutes * 60,
        )
