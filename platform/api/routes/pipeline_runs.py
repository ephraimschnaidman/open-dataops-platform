from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import AwareDatetime

from api.repositories.pipeline_runs import PipelineRunFilters, PipelineRunRepository
from api.schemas.core_resources import ApiErrorResponse, RunStatus, StageName
from api.schemas.pipeline_runs import PipelineRunDetail, PipelineRunListResponse
from api.services.pipeline_runs import PipelineRunNotFoundError, PipelineRunService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/pipeline-runs", tags=["pipeline-runs"])


def get_pipeline_run_service(request: Request) -> PipelineRunService:
    return PipelineRunService(PipelineRunRepository(request.app.state.database_pool))


@router.get("", response_model=PipelineRunListResponse, responses={503: {"model": ApiErrorResponse}})
async def list_pipeline_runs(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    pipeline: Annotated[str | None, Query(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")] = None,
    environment: Annotated[str | None, Query(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")] = None,
    status: RunStatus | None = None,
    stage: StageName | None = None,
    source: Annotated[str | None, Query(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")] = None,
    started_from: AwareDatetime | None = None,
    started_to: AwareDatetime | None = None,
    search: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    service: PipelineRunService = Depends(get_pipeline_run_service),
) -> PipelineRunListResponse:
    if started_from is not None and started_to is not None and started_from > started_to:
        raise HTTPException(status_code=422, detail="started_from must be before or equal to started_to")
    try:
        return await service.list_pipeline_runs(
            limit=limit,
            offset=offset,
            filters=PipelineRunFilters(
                pipeline=pipeline,
                environment=environment,
                status=status,
                stage=stage,
                source=source,
                started_from=started_from,
                started_to=started_to,
                search=search,
            ),
        )
    except Exception as error:
        logger.warning("Pipeline run list query failed", extra={"event": "pipeline_run_list_query_failed"}, exc_info=error)
        raise HTTPException(status_code=503, detail="Database unavailable") from error


@router.get("/{corvetra_run_id}", response_model=PipelineRunDetail, responses={404: {"model": ApiErrorResponse}, 503: {"model": ApiErrorResponse}})
async def get_pipeline_run(
    corvetra_run_id: Annotated[str, Path(pattern=r"^run_[A-Za-z0-9]+$")],
    service: PipelineRunService = Depends(get_pipeline_run_service),
) -> PipelineRunDetail:
    try:
        return await service.get_pipeline_run(corvetra_run_id)
    except PipelineRunNotFoundError as error:
        raise HTTPException(status_code=404, detail="Pipeline run not found") from error
    except Exception as error:
        logger.warning("Pipeline run detail query failed", extra={"event": "pipeline_run_detail_query_failed"}, exc_info=error)
        raise HTTPException(status_code=503, detail="Database unavailable") from error
