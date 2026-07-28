from __future__ import annotations

from api.repositories.pipelines import PipelineFilters, PipelineRepository
from api.schemas.pipelines import (
    PipelineListResponse,
    PipelinePaginationMetadata,
    PipelineResponse,
)


class PipelineService:
    def __init__(self, repository: PipelineRepository) -> None:
        self._repository = repository

    async def list_pipelines(
        self,
        *,
        limit: int,
        offset: int,
        filters: PipelineFilters,
    ) -> PipelineListResponse:
        rows, total = await self._repository.list_pipelines(
            limit=limit,
            offset=offset,
            filters=filters,
        )
        items = [PipelineResponse.model_validate(row) for row in rows]
        return PipelineListResponse(
            items=items,
            pagination=PipelinePaginationMetadata(
                limit=limit,
                offset=offset,
                total=total,
                returned_count=len(items),
            ),
        )
