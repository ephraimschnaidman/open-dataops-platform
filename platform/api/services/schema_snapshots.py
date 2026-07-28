from __future__ import annotations

from api.repositories.schema_snapshots import (
    SchemaSnapshotFilters,
    SchemaSnapshotRepository,
)
from api.schemas.schema_snapshots import (
    SchemaSnapshotListResponse,
    SchemaSnapshotPaginationMetadata,
    SchemaSnapshotResponse,
)


class SchemaSnapshotService:
    def __init__(self, repository: SchemaSnapshotRepository) -> None:
        self._repository = repository

    async def list_schema_snapshots(
        self,
        *,
        limit: int,
        offset: int,
        filters: SchemaSnapshotFilters,
        latest: bool,
    ) -> SchemaSnapshotListResponse:
        rows, total = await self._repository.list_schema_snapshots(
            limit=limit,
            offset=offset,
            filters=filters,
            latest=latest,
        )
        items = [SchemaSnapshotResponse.model_validate(row) for row in rows]
        return SchemaSnapshotListResponse(
            items=items,
            pagination=SchemaSnapshotPaginationMetadata(
                limit=limit,
                offset=offset,
                total=total,
                returned_count=len(items),
            ),
        )
