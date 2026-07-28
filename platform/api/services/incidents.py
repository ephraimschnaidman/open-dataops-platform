from __future__ import annotations

from uuid import UUID

from api.repositories.incidents import IncidentFilters, IncidentRepository
from api.schemas.incidents import (
    IncidentContextResponse,
    IncidentDetailResponse,
    IncidentListResponse,
    IncidentResponse,
    PaginationMetadata,
)


class IncidentNotFoundError(LookupError):
    pass


class IncidentService:
    def __init__(self, repository: IncidentRepository) -> None:
        self._repository = repository

    async def list_incidents(
        self,
        *,
        limit: int,
        offset: int,
        filters: IncidentFilters,
    ) -> IncidentListResponse:
        rows, total = await self._repository.list_incidents(
            limit=limit,
            offset=offset,
            filters=filters,
        )
        items = [IncidentResponse.model_validate(row) for row in rows]
        return IncidentListResponse(
            items=items,
            pagination=PaginationMetadata(
                limit=limit,
                offset=offset,
                total=total,
                returned_count=len(items),
            ),
        )

    async def get_incident(self, incident_id: UUID) -> IncidentDetailResponse:
        incident = await self._repository.get_incident(incident_id)
        if incident is None:
            raise IncidentNotFoundError
        context = await self._repository.get_incident_context(incident_id)
        return IncidentDetailResponse(
            **incident,
            incident_context=(
                None
                if context is None
                else IncidentContextResponse.model_validate(context)
            ),
        )
