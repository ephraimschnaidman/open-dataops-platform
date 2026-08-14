from __future__ import annotations

import re
from typing import Any

from api.repositories.logs import LogFilters, LogRepository
from api.schemas.core_resources import PaginationMetadata
from api.schemas.logs import LogEventDetail, LogEventListItem, LogEventListResponse

REDACTED = "[REDACTED]"
SENSITIVE_KEYS = {
    "credential", "credentials", "password", "passwd", "secret", "secrets",
    "token", "accesstoken", "refreshtoken", "authorization", "apikey",
    "cookie", "cookies", "privatekey", "connectionstring",
}
SENSITIVE_SUFFIXES = (
    "credential", "credentials", "password", "passwd", "secret", "token",
    "authorization", "apikey", "cookie", "privatekey", "connectionstring",
)
NON_SECRET_METADATA_SUFFIXES = ("count", "counts", "length", "type", "expiry", "expiresat")


def _normalized_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _is_sensitive_key(value: str) -> bool:
    normalized = _normalized_key(value)
    if normalized in SENSITIVE_KEYS:
        return True
    if normalized.endswith(NON_SECRET_METADATA_SUFFIXES):
        return False
    return normalized.endswith(SENSITIVE_SUFFIXES) or normalized.startswith("authorization")


def redact_sensitive_details(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: REDACTED if _is_sensitive_key(str(key))
            else redact_sensitive_details(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive_details(item) for item in value]
    return value


class LogEventNotFoundError(LookupError):
    pass


class LogService:
    def __init__(self, repository: LogRepository) -> None:
        self._repository = repository

    async def list_logs(self, *, limit: int, offset: int, filters: LogFilters) -> LogEventListResponse:
        rows, total = await self._repository.list_logs(limit=limit, offset=offset, filters=filters)
        items = [LogEventListItem.model_validate(row) for row in rows]
        return LogEventListResponse(items=items, pagination=PaginationMetadata(
            limit=limit, offset=offset, total=total, returned_count=len(items)))

    async def get_log(self, event_key: str) -> LogEventDetail:
        row = await self._repository.get_log(event_key)
        if row is None:
            raise LogEventNotFoundError
        details = redact_sensitive_details(row.pop("event_details") or {})
        interpretation = details.pop("interpretation", None)
        stack_trace = details.pop("stack_trace", None)
        return LogEventDetail.model_validate({**row, "details": details,
            "interpretation": interpretation, "stack_trace": stack_trace})
