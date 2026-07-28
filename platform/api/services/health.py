from __future__ import annotations

from api.repositories.health import HealthRepository
from api.schemas.health import HealthResponse


class HealthService:
    def __init__(
        self,
        repository: HealthRepository,
        *,
        service_name: str,
        version: str,
    ) -> None:
        self._repository = repository
        self._service_name = service_name
        self._version = version

    async def check(self) -> HealthResponse:
        if not await self._repository.database_is_healthy():
            raise RuntimeError("Database health query returned an unexpected result")
        return HealthResponse(
            status="healthy",
            database="healthy",
            service=self._service_name,
            version=self._version,
        )
