from __future__ import annotations

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import AwareDatetime

from api.repositories.logs import LogFilters, LogRepository
from api.schemas.core_resources import ApiErrorResponse, EventLevel, StageName
from api.schemas.logs import LogEventDetail, LogEventListResponse
from api.services.logs import LogEventNotFoundError, LogService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/logs", tags=["logs"])


def get_log_service(request: Request) -> LogService:
    return LogService(LogRepository(request.app.state.database_pool))


@router.get("", response_model=LogEventListResponse, responses={503: {"model": ApiErrorResponse}})
async def list_logs(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    environment: Annotated[str | None, Query(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")] = None,
    pipeline: Annotated[str | None, Query(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")] = None,
    run: Annotated[str | None, Query(pattern=r"^run_[A-Za-z0-9]+$")] = None,
    source: Annotated[str | None, Query(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")] = None,
    stage: StageName | None = None,
    alert: Annotated[str | None, Query(pattern=r"^ALT-[0-9]+$")] = None,
    check: Annotated[str | None, Query(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")] = None,
    level: Annotated[list[EventLevel] | None, Query()] = None,
    platform_code: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    vendor_code: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    rule_code: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    occurred_from: AwareDatetime | None = None,
    occurred_to: AwareDatetime | None = None,
    search: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    sort: Literal["newest", "oldest"] = "newest",
    service: LogService = Depends(get_log_service),
) -> LogEventListResponse:
    if occurred_from is not None and occurred_to is not None and occurred_from > occurred_to:
        raise HTTPException(status_code=422, detail="occurred_from must be before or equal to occurred_to")
    try:
        return await service.list_logs(limit=limit, offset=offset, filters=LogFilters(
            environment=environment, pipeline=pipeline, run=run, source=source,
            stage=stage, alert=alert, check=check, levels=tuple(level or ()),
            platform_code=platform_code, vendor_code=vendor_code, rule_code=rule_code,
            occurred_from=occurred_from, occurred_to=occurred_to, search=search, sort=sort))
    except Exception as error:
        logger.warning("Log list query failed", extra={"event": "log_list_query_failed"}, exc_info=error)
        raise HTTPException(status_code=503, detail="Database unavailable") from error


@router.get("/{event_key}", response_model=LogEventDetail,
            responses={404: {"model": ApiErrorResponse}, 503: {"model": ApiErrorResponse}})
async def get_log(
    event_key: Annotated[str, Path(pattern=r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$")],
    service: LogService = Depends(get_log_service),
) -> LogEventDetail:
    try:
        return await service.get_log(event_key)
    except LogEventNotFoundError as error:
        raise HTTPException(status_code=404, detail="Log event not found") from error
    except Exception as error:
        logger.warning("Log detail query failed", extra={"event": "log_detail_query_failed"}, exc_info=error)
        raise HTTPException(status_code=503, detail="Database unavailable") from error
