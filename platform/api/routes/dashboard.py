from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from api.repositories.aggregations import AggregationRepository
from api.schemas.aggregations import DashboardResponse
from api.schemas.core_resources import ApiErrorResponse
from api.services.aggregations import AggregationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])
ProductKey = Annotated[str, Query(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]


def get_dashboard_service(request: Request) -> AggregationService:
    return AggregationService(AggregationRepository(request.app.state.database_pool))


@router.get("", response_model=DashboardResponse, responses={503: {"model": ApiErrorResponse}})
async def get_dashboard(
    environment: ProductKey | None = None,
    service: AggregationService = Depends(get_dashboard_service),
) -> DashboardResponse:
    try:
        return await service.get_dashboard(environment=environment)
    except Exception as error:
        logger.warning("Dashboard query failed", extra={"event": "dashboard_query_failed"}, exc_info=error)
        raise HTTPException(status_code=503, detail="Database unavailable") from error
