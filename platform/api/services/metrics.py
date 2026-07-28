from __future__ import annotations

from api.repositories.metrics import MetricFilters, MetricRepository
from api.schemas.metrics import (
    MetricListResponse,
    MetricPaginationMetadata,
    MetricResponse,
)


class MetricService:
    def __init__(self, repository: MetricRepository) -> None:
        self._repository = repository

    async def list_metrics(
        self,
        *,
        limit: int,
        offset: int,
        filters: MetricFilters,
        latest: bool,
    ) -> MetricListResponse:
        rows, total = await self._repository.list_metrics(
            limit=limit,
            offset=offset,
            filters=filters,
            latest=latest,
        )
        items = [MetricResponse.model_validate(row) for row in rows]
        return MetricListResponse(
            items=items,
            pagination=MetricPaginationMetadata(
                limit=limit,
                offset=offset,
                total=total,
                returned_count=len(items),
            ),
        )
