from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from api.repositories.data_sources import DataSourceFilters, DataSourceRepository
from api.schemas.core_resources import ApiErrorResponse, DataSourceOperationalStatus, SourceType
from api.schemas.data_sources import DataSourceDetail, DataSourceListResponse
from api.services.data_sources import DataSourceNotFoundError, DataSourceService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/data-sources", tags=["data-sources"])


def get_data_source_service(request: Request) -> DataSourceService:
    return DataSourceService(DataSourceRepository(request.app.state.database_pool))


@router.get("", response_model=DataSourceListResponse, responses={503: {"model": ApiErrorResponse}})
async def list_data_sources(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    environment: Annotated[str | None, Query(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")] = None,
    operational_status: DataSourceOperationalStatus | None = None,
    source_type: SourceType | None = None,
    search: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    service: DataSourceService = Depends(get_data_source_service),
) -> DataSourceListResponse:
    try:
        return await service.list_data_sources(
            limit=limit,
            offset=offset,
            filters=DataSourceFilters(
                environment=environment,
                operational_status=operational_status,
                source_type=source_type,
                search=search,
            ),
        )
    except Exception as error:
        logger.warning("Data source list query failed", extra={"event": "data_source_list_query_failed"}, exc_info=error)
        raise HTTPException(status_code=503, detail="Database unavailable") from error


@router.get("/{source_key}", response_model=DataSourceDetail, responses={404: {"model": ApiErrorResponse}, 503: {"model": ApiErrorResponse}})
async def get_data_source(
    source_key: Annotated[str, Path(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")],
    service: DataSourceService = Depends(get_data_source_service),
) -> DataSourceDetail:
    try:
        return await service.get_data_source(source_key)
    except DataSourceNotFoundError as error:
        raise HTTPException(status_code=404, detail="Data source not found") from error
    except Exception as error:
        logger.warning("Data source detail query failed", extra={"event": "data_source_detail_query_failed"}, exc_info=error)
        raise HTTPException(status_code=503, detail="Database unavailable") from error
