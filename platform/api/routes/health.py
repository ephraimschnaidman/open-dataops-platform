from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.config import Settings, get_settings
from api.repositories.health import HealthRepository
from api.schemas.health import HealthResponse, ServiceUnavailableResponse
from api.services.health import HealthService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


def get_health_service(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> HealthService:
    return HealthService(
        HealthRepository(request.app.state.database_pool),
        service_name=settings.service_name,
        version=settings.version,
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ServiceUnavailableResponse,
            "description": "PostgreSQL is unavailable.",
        }
    },
)
async def health(
    service: HealthService = Depends(get_health_service),
) -> HealthResponse:
    try:
        return await service.check()
    except Exception as error:
        logger.warning(
            "Database health check failed",
            extra={"event": "database_health_check_failed"},
            exc_info=error,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from error
