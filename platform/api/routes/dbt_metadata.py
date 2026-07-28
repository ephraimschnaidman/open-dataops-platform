from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from api.repositories.dbt_metadata import DbtMetadataFilters, DbtMetadataRepository
from api.schemas.dbt_metadata import DbtMetadataErrorResponse, DbtMetadataListResponse
from api.services.dbt_metadata import DbtMetadataService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dbt-metadata", tags=["dbt metadata"])


def get_dbt_metadata_service(request: Request) -> DbtMetadataService:
    return DbtMetadataService(DbtMetadataRepository(request.app.state.database_pool))


@router.get(
    "",
    response_model=DbtMetadataListResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": DbtMetadataErrorResponse,
            "description": "PostgreSQL is unavailable.",
        }
    },
)
async def list_dbt_metadata(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    pipeline_run_id: UUID | None = None,
    invocation_id: str | None = None,
    resource_type: str | None = None,
    execution_status: str | None = None,
    node_name: str | None = None,
    service: DbtMetadataService = Depends(get_dbt_metadata_service),
) -> DbtMetadataListResponse:
    try:
        return await service.list_dbt_metadata(
            limit=limit,
            offset=offset,
            filters=DbtMetadataFilters(
                pipeline_run_id=pipeline_run_id,
                invocation_id=invocation_id,
                resource_type=resource_type,
                execution_status=execution_status,
                node_name=node_name,
            ),
        )
    except Exception as error:
        logger.warning(
            "dbt metadata list query failed",
            extra={"event": "dbt_metadata_list_query_failed"},
            exc_info=error,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from error
