from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request, status
from fastapi.responses import JSONResponse

from api.auth_dependencies import require_roles
from api.repositories.settings import SettingsRepository
from api.schemas.settings import (
    EnvironmentCreate, GeneralSettingsUpdate, NotificationSettings,
    OperationalDefaults, SettingsErrorResponse, SettingsResponse,
)
from api.services.settings import (
    DefaultEnvironmentRequiredError, EnvironmentInUseError,
    EnvironmentNotFoundError, SettingsService,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/settings", tags=["settings"])
require_admin = require_roles("Admin")
WRITE_DEPENDENCIES = [Depends(require_admin)]
ERROR_RESPONSES = {404: {"model": SettingsErrorResponse}, 409: {"model": SettingsErrorResponse}, 503: {"model": SettingsErrorResponse}}


def get_settings_service(request: Request) -> SettingsService:
    return SettingsService(SettingsRepository(request.app.state.database_pool))


def error_response(status_code: int, code: str, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail, "code": code})


@router.get("", response_model=SettingsResponse, responses=ERROR_RESPONSES)
async def get_settings(service: SettingsService = Depends(get_settings_service)):
    try:
        return await service.get_settings()
    except Exception as error:
        logger.warning("Settings query failed", extra={"event": "settings_query_failed"}, exc_info=error)
        return error_response(503, "SETTINGS_UNAVAILABLE", "Workspace settings are unavailable")


@router.put("/notifications", response_model=NotificationSettings, responses=ERROR_RESPONSES, dependencies=WRITE_DEPENDENCIES)
async def update_notifications(settings: NotificationSettings, service: SettingsService = Depends(get_settings_service)):
    try:
        return await service.update_notifications(settings)
    except Exception as error:
        logger.warning("Notification settings update failed", extra={"event": "notification_settings_update_failed"}, exc_info=error)
        return error_response(503, "NOTIFICATION_UPDATE_FAILED", "Notification settings could not be saved")


@router.put("/operational-defaults", response_model=OperationalDefaults, responses=ERROR_RESPONSES, dependencies=WRITE_DEPENDENCIES)
async def update_operational_defaults(settings: OperationalDefaults, service: SettingsService = Depends(get_settings_service)):
    try:
        return await service.update_operational_defaults(settings)
    except Exception as error:
        logger.warning("Operational defaults update failed", extra={"event": "operational_defaults_update_failed"}, exc_info=error)
        return error_response(503, "OPERATIONAL_DEFAULTS_UPDATE_FAILED", "Operational defaults could not be saved")


@router.put("/general", response_model=SettingsResponse, responses=ERROR_RESPONSES, dependencies=WRITE_DEPENDENCIES)
async def update_general(settings: GeneralSettingsUpdate, service: SettingsService = Depends(get_settings_service)):
    try:
        return await service.update_general(settings)
    except EnvironmentNotFoundError:
        return error_response(404, "ENVIRONMENT_NOT_FOUND", "The selected environment does not exist")
    except Exception as error:
        logger.warning("General settings update failed", extra={"event": "general_settings_update_failed"}, exc_info=error)
        return error_response(503, "SETTINGS_UPDATE_FAILED", "Workspace settings could not be saved")


@router.post("/environments", response_model=SettingsResponse, status_code=status.HTTP_201_CREATED, responses=ERROR_RESPONSES, dependencies=WRITE_DEPENDENCIES)
async def create_environment(environment: EnvironmentCreate, service: SettingsService = Depends(get_settings_service)):
    try:
        return await service.create_environment(environment)
    except Exception as error:
        logger.warning("Environment creation failed", extra={"event": "environment_creation_failed"}, exc_info=error)
        return error_response(409, "ENVIRONMENT_ALREADY_EXISTS", "An environment with this identifier or name already exists")


@router.delete("/environments/{environment_key}", status_code=status.HTTP_204_NO_CONTENT, responses=ERROR_RESPONSES, dependencies=WRITE_DEPENDENCIES)
async def delete_environment(
    environment_key: Annotated[str, Path(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")],
    service: SettingsService = Depends(get_settings_service),
):
    try:
        await service.delete_environment(environment_key)
        return None
    except EnvironmentNotFoundError:
        return error_response(404, "ENVIRONMENT_NOT_FOUND", "The environment does not exist")
    except DefaultEnvironmentRequiredError:
        return error_response(409, "DEFAULT_ENVIRONMENT_REQUIRED", "Assign another workspace default before deleting this environment")
    except EnvironmentInUseError:
        return error_response(409, "ENVIRONMENT_IN_USE", "The environment still contains resources")
    except Exception as error:
        logger.warning("Environment deletion failed", extra={"event": "environment_deletion_failed"}, exc_info=error)
        return error_response(503, "ENVIRONMENT_DELETE_FAILED", "The environment could not be deleted")
