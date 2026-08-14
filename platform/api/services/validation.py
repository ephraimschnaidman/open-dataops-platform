from __future__ import annotations

from api.repositories.validation import ValidationFilters, ValidationRepository
from api.schemas.core_resources import PaginationMetadata
from api.schemas.validation import ValidationExecutionDetail, ValidationListItem, ValidationListResponse


class ValidationExecutionNotFoundError(LookupError):
    pass


class ValidationService:
    def __init__(self, repository: ValidationRepository) -> None:
        self._repository = repository

    async def list_validation(self, *, limit: int, offset: int, filters: ValidationFilters) -> ValidationListResponse:
        rows, total = await self._repository.list_validation(limit=limit, offset=offset, filters=filters)
        items = [ValidationListItem.model_validate(row) for row in rows]
        return ValidationListResponse(items=items, pagination=PaginationMetadata(
            limit=limit, offset=offset, total=total, returned_count=len(items)))

    async def get_execution(self, check_key: str, corvetra_run_id: str) -> ValidationExecutionDetail:
        row = await self._repository.get_execution(check_key, corvetra_run_id)
        if row is None:
            raise ValidationExecutionNotFoundError
        execution_id = row.pop("validation_execution_id")
        check_id = row.pop("validation_check_id")
        alerts = await self._repository.get_alerts(execution_id)
        count = await self._repository.count_evidence(execution_id)
        evidence = await self._repository.get_evidence(execution_id)
        history = await self._repository.get_history(check_id)
        return ValidationExecutionDetail.model_validate({**row, "related_alerts": alerts,
            "technical_evidence_count": count, "technical_evidence": evidence,
            "recent_executions": history})
