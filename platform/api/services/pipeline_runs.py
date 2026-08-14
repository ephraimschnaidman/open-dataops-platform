from __future__ import annotations

from api.repositories.pipeline_runs import PipelineRunFilters, PipelineRunRepository
from api.schemas.core_resources import PaginationMetadata
from api.schemas.pipeline_runs import PipelineRunDetail, PipelineRunListItem, PipelineRunListResponse


class PipelineRunNotFoundError(LookupError):
    pass


class PipelineRunService:
    def __init__(self, repository: PipelineRunRepository) -> None:
        self._repository = repository

    async def list_pipeline_runs(
        self, *, limit: int, offset: int, filters: PipelineRunFilters
    ) -> PipelineRunListResponse:
        rows, total = await self._repository.list_pipeline_runs(
            limit=limit, offset=offset, filters=filters
        )
        items = [PipelineRunListItem.model_validate(row) for row in rows]
        return PipelineRunListResponse(
            items=items,
            pagination=PaginationMetadata(
                limit=limit, offset=offset, total=total, returned_count=len(items)
            ),
        )

    async def get_pipeline_run(self, corvetra_run_id: str) -> PipelineRunDetail:
        row = await self._repository.get_pipeline_run(corvetra_run_id)
        if row is None:
            raise PipelineRunNotFoundError
        pipeline_run_id = row.pop("pipeline_run_id")
        alerts = await self._repository.get_alerts(pipeline_run_id)
        validation = await self._repository.get_validation_summary(pipeline_run_id)
        executions = await self._repository.get_validation_executions(pipeline_run_id)
        evidence_count = await self._repository.count_technical_evidence(pipeline_run_id)
        evidence = await self._repository.get_technical_evidence(pipeline_run_id)
        return PipelineRunDetail.model_validate(
            {
                **row,
                "alerts": alerts,
                "validation_summary": validation,
                "validation_executions": executions,
                "technical_evidence_count": evidence_count,
                "technical_evidence": evidence,
            }
        )
