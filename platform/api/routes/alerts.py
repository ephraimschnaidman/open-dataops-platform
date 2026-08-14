from __future__ import annotations

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import AwareDatetime

from api.repositories.alerts import AlertFilters, AlertRepository
from api.schemas.alerts import AlertDetail, AlertListResponse
from api.schemas.core_resources import AlertSeverity, ApiErrorResponse
from api.services.alerts import AlertNotFoundError, AlertService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])
ProductKey = Annotated[str, Query(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]


def get_alert_service(request: Request) -> AlertService:
    return AlertService(AlertRepository(request.app.state.database_pool))


@router.get("", response_model=AlertListResponse, responses={503: {"model": ApiErrorResponse}})
async def list_alerts(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    status: Literal["ACTIVE", "OPEN", "ACKNOWLEDGED", "RESOLVED"] | None = None,
    severity: AlertSeverity | None = None,
    environment: ProductKey | None = None,
    pipeline: ProductKey | None = None,
    source: ProductKey | None = None,
    platform_code: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    activity_from: AwareDatetime | None = None,
    activity_to: AwareDatetime | None = None,
    search: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    service: AlertService = Depends(get_alert_service),
) -> AlertListResponse:
    if activity_from is not None and activity_to is not None and activity_from > activity_to:
        raise HTTPException(status_code=422, detail="activity_from must be before or equal to activity_to")
    try:
        return await service.list_alerts(limit=limit, offset=offset, filters=AlertFilters(
            status=status, severity=severity, environment=environment, pipeline=pipeline,
            source=source, platform_code=platform_code, activity_from=activity_from,
            activity_to=activity_to, search=search))
    except Exception as error:
        logger.warning("Alert list query failed", extra={"event": "alert_list_query_failed"}, exc_info=error)
        raise HTTPException(status_code=503, detail="Database unavailable") from error


@router.get("/{alert_key}", response_model=AlertDetail,
            responses={404: {"model": ApiErrorResponse}, 503: {"model": ApiErrorResponse}})
async def get_alert(
    alert_key: Annotated[str, Path(pattern=r"^ALT-[0-9]+$")],
    service: AlertService = Depends(get_alert_service),
) -> AlertDetail:
    try:
        return await service.get_alert(alert_key)
    except AlertNotFoundError as error:
        raise HTTPException(status_code=404, detail="Alert not found") from error
    except Exception as error:
        logger.warning("Alert detail query failed", extra={"event": "alert_detail_query_failed"}, exc_info=error)
        raise HTTPException(status_code=503, detail="Database unavailable") from error
