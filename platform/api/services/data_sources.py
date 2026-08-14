from __future__ import annotations

from api.repositories.data_sources import DataSourceFilters, DataSourceRepository
from api.schemas.core_resources import PaginationMetadata
from api.schemas.data_sources import DataSourceDetail, DataSourceListItem, DataSourceListResponse


class DataSourceNotFoundError(LookupError):
    pass


class DataSourceService:
    def __init__(self, repository: DataSourceRepository) -> None:
        self._repository = repository

    async def list_data_sources(
        self, *, limit: int, offset: int, filters: DataSourceFilters
    ) -> DataSourceListResponse:
        rows, total = await self._repository.list_data_sources(
            limit=limit, offset=offset, filters=filters
        )
        items = [DataSourceListItem.model_validate(row) for row in rows]
        return DataSourceListResponse(
            items=items,
            pagination=PaginationMetadata(
                limit=limit, offset=offset, total=total, returned_count=len(items)
            ),
        )

    async def get_data_source(self, source_key: str) -> DataSourceDetail:
        row = await self._repository.get_data_source(source_key)
        if row is None:
            raise DataSourceNotFoundError
        data_source_id = row.pop("data_source_id")
        pipelines = await self._repository.get_connected_pipelines(data_source_id)
        validation = await self._repository.get_validation_summary(data_source_id)
        alerts = await self._repository.count_active_alerts(data_source_id)
        evidence = await self._repository.get_recent_evidence(data_source_id)
        return DataSourceDetail.model_validate(
            {
                **row,
                "connected_pipelines": pipelines,
                "validation_summary": validation,
                "active_alert_count": alerts,
                "recent_evidence": evidence,
            }
        )
