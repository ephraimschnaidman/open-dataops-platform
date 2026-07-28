from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from api.repositories.pipelines import PipelineFilters, PipelineRepository
from api.schemas.pipelines import PipelineErrorResponse, PipelineListResponse
from api.services.pipelines import PipelineService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pipelines", tags=["pipelines"])


def get_pipeline_service(request: Request) -> PipelineService:
    return PipelineService(PipelineRepository(request.app.state.database_pool))


@router.get(
    "",
    response_model=PipelineListResponse,
    summary="List collected pipeline runs",
    description=(
        "Returns persisted pipeline execution history. Runs that fail before "
        "the metadata collection stage may not be represented."
    ),
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": PipelineErrorResponse,
            "description": "PostgreSQL is unavailable.",
        }
    },
)
async def list_pipelines(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    dag_id: str | None = None,
    run_status: str | None = None,
    pipeline_run_id: UUID | None = None,
    airflow_run_id: str | None = None,
    service: PipelineService = Depends(get_pipeline_service),
) -> PipelineListResponse:
    try:
        return await service.list_pipelines(
            limit=limit,
            offset=offset,
            filters=PipelineFilters(
                dag_id=dag_id,
                run_status=run_status,
                pipeline_run_id=pipeline_run_id,
                airflow_run_id=airflow_run_id,
            ),
        )
    except Exception as error:
        logger.warning(
            "Pipeline list query failed",
            extra={"event": "pipeline_list_query_failed"},
            exc_info=error,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from error
