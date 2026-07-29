from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RepositoryUser(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    username: str
    password_hash: str
    is_active: bool
    roles: list[str]


class CurrentUser(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    username: str
    is_active: bool
    roles: list[str]


class TokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(gt=0)


class AuthenticationErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: str
