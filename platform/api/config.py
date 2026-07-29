from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

REPO_ROOT = Path(__file__).resolve().parents[2]
JWT_ALGORITHM = "HS256"

_JWT_SECRET_PLACEHOLDER_MARKERS = (
    "change_this",
    "changeme",
    "placeholder",
    "replace",
    "your_secret",
)


def parse_boolean_environment(value: str, *, variable_name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(
        f"{variable_name} must be one of true/false, 1/0, yes/no, or on/off"
    )


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    service_name: str = "Open DataOps Platform API"
    version: str = "0.1.0"
    log_level: str = "INFO"
    postgres_host: str = "localhost"
    postgres_port: int = Field(default=5433, ge=1, le=65535)
    postgres_db: str = "dataops"
    postgres_user: str = "dataops"
    postgres_password: str = ""
    database_pool_min_size: int = Field(default=1, ge=0)
    database_pool_max_size: int = Field(default=5, ge=1)
    database_pool_timeout: float = Field(default=5.0, gt=0)
    jwt_secret_key: str = Field(min_length=32)
    jwt_access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)
    jwt_issuer: str
    jwt_audience: str
    api_docs_enabled: bool = False

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("JWT secret key must not be blank")
        normalized = value.strip().lower()
        if any(marker in normalized for marker in _JWT_SECRET_PLACEHOLDER_MARKERS):
            raise ValueError("JWT secret key must not be a placeholder")
        return value

    @field_validator("jwt_issuer", "jwt_audience")
    @classmethod
    def validate_nonblank_jwt_identifier(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("JWT issuer and audience must not be blank")
        return normalized

    @model_validator(mode="after")
    def validate_pool_sizes(self) -> "Settings":
        if self.database_pool_min_size > self.database_pool_max_size:
            raise ValueError(
                "database_pool_min_size must be less than or equal to "
                "database_pool_max_size"
            )
        return self

    @classmethod
    def from_environment(cls) -> "Settings":
        load_dotenv(REPO_ROOT / ".env")
        docs_enabled = parse_boolean_environment(
            os.getenv("API_DOCS_ENABLED", "false"),
            variable_name="API_DOCS_ENABLED",
        )
        return cls(
            service_name=os.getenv("API_SERVICE_NAME", cls.model_fields["service_name"].default),
            version=os.getenv("API_VERSION", cls.model_fields["version"].default),
            log_level=os.getenv("API_LOG_LEVEL", cls.model_fields["log_level"].default),
            postgres_host=os.getenv("POSTGRES_HOST", cls.model_fields["postgres_host"].default),
            postgres_port=os.getenv(
                "POSTGRES_PORT",
                str(cls.model_fields["postgres_port"].default),
            ),
            postgres_db=os.getenv("POSTGRES_DB", cls.model_fields["postgres_db"].default),
            postgres_user=os.getenv("POSTGRES_USER", cls.model_fields["postgres_user"].default),
            postgres_password=os.getenv("POSTGRES_PASSWORD", ""),
            database_pool_min_size=os.getenv("API_DB_POOL_MIN_SIZE", "1"),
            database_pool_max_size=os.getenv("API_DB_POOL_MAX_SIZE", "5"),
            database_pool_timeout=os.getenv("API_DB_POOL_TIMEOUT", "5"),
            jwt_secret_key=os.getenv("API_JWT_SECRET_KEY"),
            jwt_access_token_expire_minutes=os.getenv(
                "API_JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
                "30",
            ),
            jwt_issuer=os.getenv("API_JWT_ISSUER"),
            jwt_audience=os.getenv("API_JWT_AUDIENCE"),
            api_docs_enabled=docs_enabled,
        )

    def database_connection_kwargs(self) -> dict[str, str | int]:
        return {
            "host": self.postgres_host,
            "port": self.postgres_port,
            "dbname": self.postgres_db,
            "user": self.postgres_user,
            "password": self.postgres_password,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings.from_environment()
