from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from api.repositories.metrics import MetricFilters, MetricRepository
from api.schemas.metrics import MetricErrorResponse, MetricListResponse
from api.services.metrics import MetricService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


def get_metric_service(request: Request) -> MetricService:
    return MetricService(MetricRepository(request.app.state.database_pool))


@router.get(
    "",
    response_model=MetricListResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": MetricErrorResponse,
            "description": "PostgreSQL is unavailable.",
        }
    },
)
async def list_metrics(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    pipeline_run_id: UUID | None = None,
    table_schema: str | None = None,
    table_name: str | None = None,
    latest: bool = False,
    service: MetricService = Depends(get_metric_service),
) -> MetricListResponse:
    try:
        return await service.list_metrics(
            limit=limit,
            offset=offset,
            filters=MetricFilters(
                pipeline_run_id=pipeline_run_id,
                table_schema=table_schema,
                table_name=table_name,
            ),
            latest=latest,
        )
    except Exception as error:
        logger.warning(
            "Metric list query failed",
            extra={"event": "metric_list_query_failed"},
            exc_info=error,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from error
