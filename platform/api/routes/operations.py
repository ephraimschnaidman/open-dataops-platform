from __future__ import annotations

from datetime import datetime
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.auth_dependencies import require_roles
from api.dependencies import get_pipeline_operations_service
from api.orchestrators.base import (
    OrchestratorAuthenticationError, OrchestratorConflictError,
    OrchestratorInvalidResponseError, OrchestratorNotFoundError,
    OrchestratorOperationUnsupportedError, OrchestratorPermissionError,
    OrchestratorUnavailableError,
)
from api.schemas.operations import (
    DagListResponse, DagResponse, DagRunListResponse, DagRunResponse,
    OperationsErrorResponse, TaskInstanceListResponse, TaskLogResponse,
    TriggerDagRequest, WorkflowOperationResponse,
)
from api.services.pipeline_operations import PipelineOperationsService

router = APIRouter(prefix="/api/v1/operations", tags=["operations"])
Service = Annotated[PipelineOperationsService, Depends(get_pipeline_operations_service)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]
require_write_access = require_roles("Admin", "Operator")
WRITE_DEPENDENCIES = [Depends(require_write_access)]

ERROR_RESPONSES = {
    404: {"model": OperationsErrorResponse},
    409: {"model": OperationsErrorResponse},
    501: {"model": OperationsErrorResponse},
    503: {"model": OperationsErrorResponse},
}


def _raise_safe(error: Exception) -> NoReturn:
    if isinstance(error, OrchestratorNotFoundError):
        raise HTTPException(404, "Pipeline resource not found") from error
    if isinstance(error, OrchestratorConflictError):
        raise HTTPException(409, "Pipeline operation conflict") from error
    if isinstance(error, OrchestratorOperationUnsupportedError):
        raise HTTPException(501, "Pipeline operation not supported") from error
    if isinstance(error, (
        OrchestratorUnavailableError, OrchestratorAuthenticationError,
        OrchestratorPermissionError, OrchestratorInvalidResponseError,
    )):
        raise HTTPException(503, "Pipeline service unavailable") from error
    raise error


@router.post(
    "/dags/{dag_id}/trigger",
    response_model=WorkflowOperationResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
    dependencies=WRITE_DEPENDENCIES,
)
async def trigger_dag(
    dag_id: str, request: TriggerDagRequest, service: Service
) -> WorkflowOperationResponse:
    try:
        return await service.trigger_workflow(
            dag_id=dag_id,
            run_id=request.run_id,
            logical_date=request.logical_date,
            conf=request.conf,
        )
    except Exception as error:
        _raise_safe(error)


@router.post(
    "/dags/{dag_id}/runs/{run_id}/retry",
    response_model=WorkflowOperationResponse,
    responses=ERROR_RESPONSES,
    dependencies=WRITE_DEPENDENCIES,
)
async def retry_dag_run(
    dag_id: str, run_id: str, service: Service
) -> WorkflowOperationResponse:
    try:
        return await service.retry_run(dag_id=dag_id, run_id=run_id)
    except Exception as error:
        _raise_safe(error)


@router.post(
    "/dags/{dag_id}/runs/{run_id}/cancel",
    response_model=WorkflowOperationResponse,
    responses=ERROR_RESPONSES,
    dependencies=WRITE_DEPENDENCIES,
)
async def cancel_dag_run(
    dag_id: str, run_id: str, service: Service
) -> WorkflowOperationResponse:
    try:
        return await service.cancel_run(dag_id=dag_id, run_id=run_id)
    except Exception as error:
        _raise_safe(error)


@router.get("/dags", response_model=DagListResponse, responses=ERROR_RESPONSES)
async def list_dags(
    service: Service, limit: Limit = 50, offset: Offset = 0,
    paused: bool | None = None, active: bool | None = None,
    tag: Annotated[str | None, Query(min_length=1)] = None,
) -> DagListResponse:
    try:
        return await service.list_dags(
            limit=limit, offset=offset, paused=paused, active=active, tag=tag
        )
    except Exception as error:
        _raise_safe(error)


@router.get("/dags/{dag_id}", response_model=DagResponse, responses=ERROR_RESPONSES)
async def get_dag(dag_id: str, service: Service) -> DagResponse:
    try:
        return await service.get_dag(dag_id)
    except Exception as error:
        _raise_safe(error)


@router.get("/runs", response_model=DagRunListResponse, responses=ERROR_RESPONSES)
async def list_runs(
    service: Service, limit: Limit = 50, offset: Offset = 0,
    dag_id: Annotated[str | None, Query(min_length=1)] = None,
    start_date_gte: datetime | None = None, start_date_lte: datetime | None = None,
) -> DagRunListResponse:
    if start_date_gte and start_date_lte and start_date_gte > start_date_lte:
        raise HTTPException(422, "start_date_gte must not be after start_date_lte")
    try:
        return await service.list_dag_runs(
            dag_id=dag_id, limit=limit, offset=offset,
            start_date_gte=start_date_gte.isoformat() if start_date_gte else None,
            start_date_lte=start_date_lte.isoformat() if start_date_lte else None,
        )
    except Exception as error:
        _raise_safe(error)


@router.get(
    "/dags/{dag_id}/runs/{run_id}", response_model=DagRunResponse,
    responses=ERROR_RESPONSES,
)
async def get_run(dag_id: str, run_id: str, service: Service) -> DagRunResponse:
    try:
        return await service.get_dag_run(dag_id=dag_id, run_id=run_id)
    except Exception as error:
        _raise_safe(error)


@router.get(
    "/dags/{dag_id}/runs/{run_id}/tasks",
    response_model=TaskInstanceListResponse, responses=ERROR_RESPONSES,
)
async def list_tasks(
    dag_id: str, run_id: str, service: Service,
    limit: Limit = 100, offset: Offset = 0,
) -> TaskInstanceListResponse:
    try:
        return await service.list_task_instances(
            dag_id=dag_id, run_id=run_id, limit=limit, offset=offset
        )
    except Exception as error:
        _raise_safe(error)


@router.get(
    "/dags/{dag_id}/runs/{run_id}/tasks/{task_id}/logs",
    response_model=TaskLogResponse, responses=ERROR_RESPONSES,
)
async def get_task_logs(
    dag_id: str, run_id: str, task_id: str, service: Service,
    try_number: Annotated[int, Query(ge=1)] = 1,
    map_index: Annotated[int, Query(ge=-1)] = -1,
) -> TaskLogResponse:
    try:
        return await service.get_task_log(
            dag_id=dag_id, run_id=run_id, task_id=task_id,
            try_number=try_number, map_index=map_index,
        )
    except Exception as error:
        _raise_safe(error)
