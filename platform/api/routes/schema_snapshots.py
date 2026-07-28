from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from api.repositories.schema_snapshots import (
    SchemaSnapshotFilters,
    SchemaSnapshotRepository,
)
from api.schemas.schema_snapshots import (
    SchemaSnapshotErrorResponse,
    SchemaSnapshotListResponse,
)
from api.services.schema_snapshots import SchemaSnapshotService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/schema-snapshots",
    tags=["schema snapshots"],
)


def get_schema_snapshot_service(request: Request) -> SchemaSnapshotService:
    return SchemaSnapshotService(
        SchemaSnapshotRepository(request.app.state.database_pool)
    )


@router.get(
    "",
    response_model=SchemaSnapshotListResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": SchemaSnapshotErrorResponse,
            "description": "PostgreSQL is unavailable.",
        }
    },
)
async def list_schema_snapshots(
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    pipeline_run_id: UUID | None = None,
    table_schema: str | None = None,
    table_name: str | None = None,
    column_name: str | None = None,
    latest: bool = False,
    service: SchemaSnapshotService = Depends(get_schema_snapshot_service),
) -> SchemaSnapshotListResponse:
    try:
        return await service.list_schema_snapshots(
            limit=limit,
            offset=offset,
            filters=SchemaSnapshotFilters(
                pipeline_run_id=pipeline_run_id,
                table_schema=table_schema,
                table_name=table_name,
                column_name=column_name,
            ),
            latest=latest,
        )
    except Exception as error:
        logger.warning(
            "Schema snapshot list query failed",
            extra={"event": "schema_snapshot_list_query_failed"},
            exc_info=error,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from error
