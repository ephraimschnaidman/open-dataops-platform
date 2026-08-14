from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from api.repositories.aggregations import AggregationFilters, AggregationRepository
from api.schemas.aggregations import HealthMetricsResponse, HealthWindow
from api.schemas.core_resources import ApiErrorResponse
from api.services.aggregations import AggregationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/health-metrics", tags=["health-metrics"])
ProductKey = Annotated[str, Query(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]


def get_health_metrics_service(request: Request) -> AggregationService:
    return AggregationService(AggregationRepository(request.app.state.database_pool))


@router.get("", response_model=HealthMetricsResponse, responses={503: {"model": ApiErrorResponse}})
async def get_health_metrics(
    window: HealthWindow = "7d",
    environment: ProductKey | None = None,
    pipeline: ProductKey | None = None,
    source: ProductKey | None = None,
    service: AggregationService = Depends(get_health_metrics_service),
) -> HealthMetricsResponse:
    if pipeline is not None and source is not None:
        raise HTTPException(status_code=422, detail="pipeline and source are mutually exclusive")
    try:
        return await service.get_health_metrics(
            window=window,
            filters=AggregationFilters(environment=environment, pipeline=pipeline, source=source),
        )
    except Exception as error:
        logger.warning("Health metrics query failed", extra={"event": "health_metrics_query_failed"}, exc_info=error)
        raise HTTPException(status_code=503, detail="Database unavailable") from error
