from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from api.repositories.incidents import IncidentFilters, IncidentRepository
from api.schemas.incidents import (
    ApiErrorResponse,
    IncidentDetailResponse,
    IncidentListResponse,
)
from api.services.incidents import IncidentNotFoundError, IncidentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])


def get_incident_service(request: Request) -> IncidentService:
    return IncidentService(IncidentRepository(request.app.state.database_pool))


@router.get(
    "",
    response_model=IncidentListResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ApiErrorResponse,
            "description": "PostgreSQL is unavailable.",
        }
    },
)
async def list_incidents(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    incident_status: str | None = None,
    severity: str | None = None,
    incident_type: str | None = None,
    table_schema: str | None = None,
    table_name: str | None = None,
    pipeline_run_id: UUID | None = None,
    service: IncidentService = Depends(get_incident_service),
) -> IncidentListResponse:
    try:
        return await service.list_incidents(
            limit=limit,
            offset=offset,
            filters=IncidentFilters(
                incident_status=incident_status,
                severity=severity,
                incident_type=incident_type,
                table_schema=table_schema,
                table_name=table_name,
                pipeline_run_id=pipeline_run_id,
            ),
        )
    except Exception as error:
        logger.warning(
            "Incident list query failed",
            extra={"event": "incident_list_query_failed"},
            exc_info=error,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from error


@router.get(
    "/{incident_id}",
    response_model=IncidentDetailResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ApiErrorResponse,
            "description": "Incident not found.",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ApiErrorResponse,
            "description": "PostgreSQL is unavailable.",
        },
    },
)
async def get_incident(
    incident_id: UUID,
    service: IncidentService = Depends(get_incident_service),
) -> IncidentDetailResponse:
    try:
        return await service.get_incident(incident_id)
    except IncidentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        ) from error
    except Exception as error:
        logger.warning(
            "Incident detail query failed",
            extra={"event": "incident_detail_query_failed"},
            exc_info=error,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from error
