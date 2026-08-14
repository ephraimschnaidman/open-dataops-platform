from __future__ import annotations

from api.repositories.alerts import AlertFilters, AlertRepository
from api.schemas.alerts import AlertDetail, AlertListItem, AlertListResponse
from api.schemas.core_resources import PaginationMetadata


class AlertNotFoundError(LookupError):
    pass


class AlertService:
    def __init__(self, repository: AlertRepository) -> None:
        self._repository = repository

    async def list_alerts(self, *, limit: int, offset: int, filters: AlertFilters) -> AlertListResponse:
        rows, total = await self._repository.list_alerts(limit=limit, offset=offset, filters=filters)
        items = [AlertListItem.model_validate(row) for row in rows]
        return AlertListResponse(items=items, pagination=PaginationMetadata(
            limit=limit, offset=offset, total=total, returned_count=len(items)))

    async def get_alert(self, alert_key: str) -> AlertDetail:
        row = await self._repository.get_alert(alert_key)
        if row is None:
            raise AlertNotFoundError
        row.pop("alert_id")
        pipeline_run_id = row.pop("pipeline_run_id")
        count = await self._repository.count_evidence(pipeline_run_id)
        evidence = await self._repository.get_evidence(pipeline_run_id)
        return AlertDetail.model_validate({**row, "technical_evidence_count": count,
                                           "recent_technical_evidence": evidence})
