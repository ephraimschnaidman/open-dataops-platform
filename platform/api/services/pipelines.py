from __future__ import annotations

from api.repositories.pipelines import PipelineFilters, PipelineRepository
from api.schemas.core_resources import PaginationMetadata
from api.schemas.pipelines import PipelineDetail, PipelineListItem, PipelineListResponse


class PipelineNotFoundError(LookupError):
    pass


class PipelineService:
    def __init__(self, repository: PipelineRepository) -> None:
        self._repository = repository

    async def list_pipelines(
        self, *, limit: int, offset: int, filters: PipelineFilters
    ) -> PipelineListResponse:
        rows, total = await self._repository.list_pipelines(
            limit=limit, offset=offset, filters=filters
        )
        items = [PipelineListItem.model_validate(row) for row in rows]
        return PipelineListResponse(
            items=items,
            pagination=PaginationMetadata(
                limit=limit, offset=offset, total=total, returned_count=len(items)
            ),
        )

    async def get_pipeline(self, pipeline_key: str) -> PipelineDetail:
        row = await self._repository.get_pipeline(pipeline_key)
        if row is None:
            raise PipelineNotFoundError
        pipeline_id = row.pop("pipeline_id")
        recent_runs = await self._repository.get_recent_runs(pipeline_id)
        validation_summary = await self._repository.get_validation_summary(pipeline_id)
        active_alerts = await self._repository.get_active_alerts(pipeline_id)
        evidence_count = await self._repository.count_technical_evidence(pipeline_id)
        return PipelineDetail.model_validate(
            {
                **row,
                "recent_runs": recent_runs,
                "validation_summary": validation_summary,
                "active_alerts": active_alerts,
                "technical_evidence_count": evidence_count,
            }
        )
