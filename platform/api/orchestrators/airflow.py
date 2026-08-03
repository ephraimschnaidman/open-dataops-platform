from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

import httpx
from pydantic import ValidationError

from api.config import Settings

from .base import (
    OrchestratorAuthenticationError,
    OrchestratorClient,
    OrchestratorConflictError,
    OrchestratorInvalidResponseError,
    OrchestratorNotFoundError,
    OrchestratorPermissionError,
    OrchestratorUnavailableError,
)
from .models import Dag, DagPage, DagRun, DagRunPage, Pagination

logger = logging.getLogger(__name__)

AIRFLOW_TIMEOUT = httpx.Timeout(connect=5.0, read=15.0, write=10.0, pool=5.0)
AIRFLOW_LIMITS = httpx.Limits(max_connections=20, max_keepalive_connections=10)


def create_airflow_http_client(
    settings: Settings,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=f"{str(settings.airflow_api_url).rstrip('/')}/",
        auth=(
            settings.airflow_api_username,
            settings.airflow_api_password.get_secret_value(),
        ),
        timeout=AIRFLOW_TIMEOUT,
        limits=AIRFLOW_LIMITS,
        follow_redirects=False,
        verify=settings.airflow_api_verify_tls,
        transport=transport,
    )


class AirflowClient(OrchestratorClient):
    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http_client = http_client

    async def aclose(self) -> None:
        await self._http_client.aclose()

    async def list_dags(self, *, limit: int, offset: int) -> DagPage:
        payload = await self._get_json(
            "dags",
            params={"limit": limit, "offset": offset},
            operation="list_dags",
        )
        records = self._required_list(payload, "dags")
        total = self._required_int(payload, "total_entries")
        items = tuple(self._map_dag(record) for record in records)
        return DagPage(
            items=items,
            pagination=Pagination(
                limit=limit,
                offset=offset,
                total=total,
                returned_count=len(items),
            ),
        )

    async def get_dag(self, dag_id: str) -> Dag:
        payload = await self._get_json(
            f"dags/{quote(dag_id, safe='')}",
            operation="get_dag",
        )
        return self._map_dag(payload)

    async def list_dag_runs(
        self,
        *,
        dag_id: str,
        limit: int,
        offset: int,
    ) -> DagRunPage:
        payload = await self._get_json(
            f"dags/{quote(dag_id, safe='')}/dagRuns",
            params={"limit": limit, "offset": offset},
            operation="list_dag_runs",
        )
        records = self._required_list(payload, "dag_runs")
        total = self._required_int(payload, "total_entries")
        items = tuple(self._map_dag_run(record) for record in records)
        return DagRunPage(
            items=items,
            pagination=Pagination(
                limit=limit,
                offset=offset,
                total=total,
                returned_count=len(items),
            ),
        )

    async def _get_json(
        self,
        path: str,
        *,
        params: Mapping[str, object] | None = None,
        operation: str,
    ) -> Mapping[str, Any]:
        try:
            response = await self._http_client.get(path, params=params)
        except (httpx.TimeoutException, httpx.NetworkError) as error:
            logger.warning(
                "Orchestrator request unavailable",
                extra={"event": "orchestrator_unavailable", "operation": operation},
            )
            raise OrchestratorUnavailableError("Orchestrator unavailable") from error

        self._raise_for_status(response, operation=operation)
        try:
            payload = response.json()
        except ValueError as error:
            raise OrchestratorInvalidResponseError(
                "Orchestrator returned an invalid response"
            ) from error
        if not isinstance(payload, Mapping):
            raise OrchestratorInvalidResponseError(
                "Orchestrator returned an invalid response"
            )
        return payload

    @staticmethod
    def _raise_for_status(response: httpx.Response, *, operation: str) -> None:
        exception_type = {
            401: OrchestratorAuthenticationError,
            403: OrchestratorPermissionError,
            404: OrchestratorNotFoundError,
            409: OrchestratorConflictError,
        }.get(response.status_code)
        if exception_type is not None:
            raise exception_type("Orchestrator request failed")
        if response.status_code >= 500 or response.status_code == 429:
            logger.warning(
                "Orchestrator request failed",
                extra={
                    "event": "orchestrator_request_failed",
                    "operation": operation,
                    "upstream_status": response.status_code,
                },
            )
            raise OrchestratorUnavailableError("Orchestrator unavailable")
        if response.is_error:
            raise OrchestratorInvalidResponseError(
                "Orchestrator rejected the request"
            )

    @classmethod
    def _map_dag(cls, payload: Mapping[str, Any]) -> Dag:
        try:
            tags = payload.get("tags", [])
            if not isinstance(tags, list):
                raise TypeError
            tag_names = tuple(cls._required_string(tag, "name") for tag in tags)
            return Dag(
                dag_id=cls._required_string(payload, "dag_id"),
                description=cls._optional_string(payload, "description"),
                is_active=cls._required_bool(payload, "is_active"),
                is_paused=cls._required_bool(payload, "is_paused"),
                owners=tuple(
                    cls._required_string_value(value)
                    for value in payload.get("owners", [])
                ),
                tags=tag_names,
            )
        except (KeyError, TypeError, ValidationError) as error:
            raise OrchestratorInvalidResponseError(
                "Orchestrator returned an invalid DAG response"
            ) from error

    @classmethod
    def _map_dag_run(cls, payload: Mapping[str, Any]) -> DagRun:
        try:
            return DagRun(
                dag_id=cls._required_string(payload, "dag_id"),
                run_id=cls._required_string(payload, "dag_run_id"),
                status=cls._required_string(payload, "state"),
                logical_date=payload.get("logical_date"),
                started_at=payload.get("start_date"),
                completed_at=payload.get("end_date"),
            )
        except (KeyError, TypeError, ValidationError) as error:
            raise OrchestratorInvalidResponseError(
                "Orchestrator returned an invalid DAG run response"
            ) from error

    @staticmethod
    def _required_list(payload: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
        try:
            value = payload[key]
        except KeyError as error:
            raise OrchestratorInvalidResponseError(
                "Orchestrator returned an invalid collection response"
            ) from error
        if not isinstance(value, list) or any(not isinstance(item, Mapping) for item in value):
            raise OrchestratorInvalidResponseError(
                "Orchestrator returned an invalid collection response"
            )
        return value

    @staticmethod
    def _required_int(payload: Mapping[str, Any], key: str) -> int:
        try:
            value = payload[key]
        except KeyError as error:
            raise OrchestratorInvalidResponseError(
                "Orchestrator returned invalid pagination"
            ) from error
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise OrchestratorInvalidResponseError(
                "Orchestrator returned invalid pagination"
            )
        return value

    @staticmethod
    def _required_string(payload: Mapping[str, Any], key: str) -> str:
        return AirflowClient._required_string_value(payload[key])

    @staticmethod
    def _required_string_value(value: object) -> str:
        if not isinstance(value, str) or not value:
            raise TypeError
        return value

    @staticmethod
    def _optional_string(payload: Mapping[str, Any], key: str) -> str | None:
        value = payload.get(key)
        if value is not None and not isinstance(value, str):
            raise TypeError
        return value

    @staticmethod
    def _required_bool(payload: Mapping[str, Any], key: str) -> bool:
        value = payload[key]
        if not isinstance(value, bool):
            raise TypeError
        return value
