from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status

from api.repositories.pipelines import PipelineFilters, PipelineRepository
from api.schemas.core_resources import ApiErrorResponse, PipelineOperationalStatus
from api.schemas.pipelines import PipelineDetail, PipelineListResponse
from api.services.pipelines import PipelineNotFoundError, PipelineService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/pipelines", tags=["pipelines"])


def get_pipeline_service(request: Request) -> PipelineService:
    return PipelineService(PipelineRepository(request.app.state.database_pool))


@router.get("", response_model=PipelineListResponse, responses={503: {"model": ApiErrorResponse}})
async def list_pipelines(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    environment: Annotated[str | None, Query(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")] = None,
    operational_status: PipelineOperationalStatus | None = None,
    source: Annotated[str | None, Query(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")] = None,
    enabled: bool | None = None,
    search: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    service: PipelineService = Depends(get_pipeline_service),
) -> PipelineListResponse:
    try:
        return await service.list_pipelines(
            limit=limit,
            offset=offset,
            filters=PipelineFilters(
                environment=environment,
                operational_status=operational_status,
                source=source,
                enabled=enabled,
                search=search,
            ),
        )
    except Exception as error:
        logger.warning("Pipeline list query failed", extra={"event": "pipeline_list_query_failed"}, exc_info=error)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable") from error


@router.get("/{pipeline_key}", response_model=PipelineDetail, responses={404: {"model": ApiErrorResponse}, 503: {"model": ApiErrorResponse}})
async def get_pipeline(
    pipeline_key: Annotated[str, Path(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")],
    service: PipelineService = Depends(get_pipeline_service),
) -> PipelineDetail:
    try:
        return await service.get_pipeline(pipeline_key)
    except PipelineNotFoundError as error:
        raise HTTPException(status_code=404, detail="Pipeline not found") from error
    except Exception as error:
        logger.warning("Pipeline detail query failed", extra={"event": "pipeline_detail_query_failed"}, exc_info=error)
        raise HTTPException(status_code=503, detail="Database unavailable") from error
