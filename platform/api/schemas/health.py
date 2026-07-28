from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["healthy"]
    database: Literal["healthy"]
    service: str
    version: str


class ServiceUnavailableResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: Literal["Database unavailable"]
