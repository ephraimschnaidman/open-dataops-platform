from __future__ import annotations

from api.repositories.dbt_metadata import DbtMetadataFilters, DbtMetadataRepository
from api.schemas.dbt_metadata import (
    DbtMetadataListResponse,
    DbtMetadataPaginationMetadata,
    DbtMetadataResponse,
)


class DbtMetadataService:
    def __init__(self, repository: DbtMetadataRepository) -> None:
        self._repository = repository

    async def list_dbt_metadata(
        self,
        *,
        limit: int,
        offset: int,
        filters: DbtMetadataFilters,
    ) -> DbtMetadataListResponse:
        rows, total = await self._repository.list_dbt_metadata(
            limit=limit,
            offset=offset,
            filters=filters,
        )
        items = [DbtMetadataResponse.model_validate(row) for row in rows]
        return DbtMetadataListResponse(
            items=items,
            pagination=DbtMetadataPaginationMetadata(
                limit=limit,
                offset=offset,
                total=total,
                returned_count=len(items),
            ),
        )
