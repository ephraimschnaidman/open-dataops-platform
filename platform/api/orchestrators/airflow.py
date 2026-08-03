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
from .models import (
    Dag, DagPage, DagRun, DagRunPage, Pagination, TaskInstance,
    TaskInstancePage, TaskLog,
)

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

    async def list_dags(
        self, *, limit: int, offset: int, paused: bool | None = None,
        active: bool | None = None, tag: str | None = None
    ) -> DagPage:
        params: dict[str, object] = {"limit": limit, "offset": offset}
        if paused is not None:
            params["paused"] = paused
        if active is not None:
            params["only_active"] = active
        if tag is not None:
            params["tags"] = tag
        payload = await self._get_json(
            "dags",
            params=params,
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
        dag_id: str | None,
        limit: int,
        offset: int,
        start_date_gte: str | None = None,
        start_date_lte: str | None = None,
    ) -> DagRunPage:
        params: dict[str, object] = {"limit": limit, "offset": offset}
        if start_date_gte is not None:
            params["start_date_gte"] = start_date_gte
        if start_date_lte is not None:
            params["start_date_lte"] = start_date_lte
        payload = await self._get_json(
            f"dags/{quote(dag_id, safe='') if dag_id is not None else '~'}/dagRuns",
            params=params,
            operation="list_dag_runs",
        )
        records = self._required_list(payload, "dag_runs")
        total = self._required_int(payload, "total_entries")
        items = tuple(self._map_dag_run(record) for record in records)
        return DagRunPage(
            items=items,
            pagination=Pagination(
                limit=limit, offset=offset, total=total, returned_count=len(items)
            ),
        )

    async def get_dag_run(self, *, dag_id: str, run_id: str) -> DagRun:
        payload = await self._get_json(
            f"dags/{quote(dag_id, safe='')}/dagRuns/{quote(run_id, safe='')}",
            operation="get_dag_run",
        )
        return self._map_dag_run(payload)

    async def list_task_instances(
        self, *, dag_id: str, run_id: str, limit: int, offset: int
    ) -> TaskInstancePage:
        payload = await self._get_json(
            f"dags/{quote(dag_id, safe='')}/dagRuns/{quote(run_id, safe='')}/taskInstances",
            params={"limit": limit, "offset": offset},
            operation="list_task_instances",
        )
        records = self._required_list(payload, "task_instances")
        total = self._required_int(payload, "total_entries")
        items = tuple(self._map_task_instance(record) for record in records)
        return TaskInstancePage(
            items=items,
            pagination=Pagination(
                limit=limit, offset=offset, total=total, returned_count=len(items)
            ),
        )

    async def get_task_log(
        self, *, dag_id: str, run_id: str, task_id: str,
        try_number: int, map_index: int
    ) -> TaskLog:
        path = (
            f"dags/{quote(dag_id, safe='')}/dagRuns/{quote(run_id, safe='')}"
            f"/taskInstances/{quote(task_id, safe='')}/logs/{try_number}"
        )
        content = await self._get_text(
            path,
            params={"full_content": True, "map_index": map_index},
            operation="get_task_log",
        )
        return TaskLog(
            dag_id=dag_id, run_id=run_id, task_id=task_id,
            try_number=try_number, map_index=map_index, content=content
        )

    async def _get_text(
        self, path: str, *, params: Mapping[str, object], operation: str
    ) -> str:
        try:
            response = await self._http_client.get(
                path, params=params, headers={"Accept": "text/plain"}
            )
        except (httpx.TimeoutException, httpx.NetworkError) as error:
            logger.warning(
                "Orchestrator request unavailable",
                extra={"event": "orchestrator_unavailable", "operation": operation},
            )
            raise OrchestratorUnavailableError("Orchestrator unavailable") from error
        self._raise_for_status(response, operation=operation)
        if response.headers.get("content-type", "").split(";", 1)[0] != "text/plain":
            raise OrchestratorInvalidResponseError(
                "Orchestrator returned an invalid log response"
            )
        return response.text

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
                display_name=cls._optional_string(payload, "dag_display_name"),
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
                state=cls._required_string(payload, "state"),
                logical_date=payload.get("logical_date"),
                start_date=payload.get("start_date"),
                end_date=payload.get("end_date"),
                data_interval_start=payload.get("data_interval_start"),
                data_interval_end=payload.get("data_interval_end"),
                run_type=cls._optional_string(payload, "run_type"),
                externally_triggered=cls._optional_bool(payload, "external_trigger"),
            )
        except (KeyError, TypeError, ValidationError) as error:
            raise OrchestratorInvalidResponseError(
                "Orchestrator returned an invalid DAG run response"
            ) from error

    @classmethod
    def _map_task_instance(cls, payload: Mapping[str, Any]) -> TaskInstance:
        try:
            state = payload.get("state")
            if state is not None and not isinstance(state, str):
                raise TypeError
            return TaskInstance(
                dag_id=cls._required_string(payload, "dag_id"),
                run_id=cls._required_string(payload, "dag_run_id"),
                task_id=cls._required_string(payload, "task_id"),
                state=state,
                try_number=cls._required_int(payload, "try_number"),
                map_index=cls._required_signed_int(payload, "map_index"),
                start_date=payload.get("start_date"),
                end_date=payload.get("end_date"),
                duration=payload.get("duration"),
                operator=cls._optional_string(payload, "operator"),
                queued_when=payload.get("queued_when"),
            )
        except (KeyError, TypeError, ValidationError) as error:
            raise OrchestratorInvalidResponseError(
                "Orchestrator returned an invalid task instance response"
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
    def _required_signed_int(payload: Mapping[str, Any], key: str) -> int:
        value = payload[key]
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError
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

    @staticmethod
    def _optional_bool(payload: Mapping[str, Any], key: str) -> bool | None:
        value = payload.get(key)
        if value is not None and not isinstance(value, bool):
            raise TypeError
        return value
