from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from api.repositories.aggregations import AggregationFilters, AggregationRepository
from api.schemas.aggregations import MonitoringResponse, MonitoringWindow
from api.schemas.core_resources import ApiErrorResponse
from api.services.aggregations import AggregationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])
ProductKey = Annotated[str, Query(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]


def get_monitoring_service(request: Request) -> AggregationService:
    return AggregationService(AggregationRepository(request.app.state.database_pool))


@router.get("", response_model=MonitoringResponse, responses={503: {"model": ApiErrorResponse}})
async def get_monitoring(
    window: MonitoringWindow = "24h",
    environment: ProductKey | None = None,
    pipeline: ProductKey | None = None,
    source: ProductKey | None = None,
    service: AggregationService = Depends(get_monitoring_service),
) -> MonitoringResponse:
    if pipeline is not None and source is not None:
        raise HTTPException(status_code=422, detail="pipeline and source are mutually exclusive")
    try:
        return await service.get_monitoring(
            window=window,
            filters=AggregationFilters(environment=environment, pipeline=pipeline, source=source),
        )
    except Exception as error:
        logger.warning("Monitoring query failed", extra={"event": "monitoring_query_failed"}, exc_info=error)
        raise HTTPException(status_code=503, detail="Database unavailable") from error
