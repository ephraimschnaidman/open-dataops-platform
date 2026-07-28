from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field

REPO_ROOT = Path(__file__).resolve().parents[2]


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

    @classmethod
    def from_environment(cls) -> "Settings":
        load_dotenv(REPO_ROOT / ".env")
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
