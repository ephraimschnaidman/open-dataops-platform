from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import AwareDatetime

from api.repositories.validation import ValidationFilters, ValidationRepository
from api.schemas.core_resources import (
    ApiErrorResponse, ValidationCheckType, ValidationResult, ValidationSeverity,
)
from api.schemas.validation import ValidationExecutionDetail, ValidationListResponse
from api.services.validation import ValidationExecutionNotFoundError, ValidationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/validation", tags=["validation"])


def get_validation_service(request: Request) -> ValidationService:
    return ValidationService(ValidationRepository(request.app.state.database_pool))


@router.get("", response_model=ValidationListResponse, responses={503: {"model": ApiErrorResponse}})
async def list_validation(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    pipeline: Annotated[str | None, Query(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")] = None,
    source: Annotated[str | None, Query(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")] = None,
    environment: Annotated[str | None, Query(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")] = None,
    run: Annotated[str | None, Query(pattern=r"^run_[A-Za-z0-9]+$")] = None,
    result: ValidationResult | None = None,
    severity: ValidationSeverity | None = None,
    check_type: ValidationCheckType | None = None,
    evaluated_from: AwareDatetime | None = None,
    evaluated_to: AwareDatetime | None = None,
    search: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    service: ValidationService = Depends(get_validation_service),
) -> ValidationListResponse:
    if evaluated_from is not None and evaluated_to is not None and evaluated_from > evaluated_to:
        raise HTTPException(status_code=422, detail="evaluated_from must be before or equal to evaluated_to")
    try:
        return await service.list_validation(limit=limit, offset=offset, filters=ValidationFilters(
            pipeline=pipeline, source=source, environment=environment, run=run,
            result=result, severity=severity, check_type=check_type,
            evaluated_from=evaluated_from, evaluated_to=evaluated_to, search=search))
    except Exception as error:
        logger.warning("Validation list query failed", extra={"event": "validation_list_query_failed"}, exc_info=error)
        raise HTTPException(status_code=503, detail="Database unavailable") from error


@router.get("/{check_key}/runs/{corvetra_run_id}", response_model=ValidationExecutionDetail,
            responses={404: {"model": ApiErrorResponse}, 503: {"model": ApiErrorResponse}})
async def get_validation_execution(
    check_key: Annotated[str, Path(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")],
    corvetra_run_id: Annotated[str, Path(pattern=r"^run_[A-Za-z0-9]+$")],
    service: ValidationService = Depends(get_validation_service),
) -> ValidationExecutionDetail:
    try:
        return await service.get_execution(check_key, corvetra_run_id)
    except ValidationExecutionNotFoundError as error:
        raise HTTPException(status_code=404, detail="Validation execution not found") from error
    except Exception as error:
        logger.warning("Validation detail query failed", extra={"event": "validation_detail_query_failed"}, exc_info=error)
        raise HTTPException(status_code=503, detail="Database unavailable") from error
