from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from api.orchestrators.base import OrchestratorClient
from api.services.pipeline_operations import PipelineOperationsService


def get_orchestrator_client(request: Request) -> OrchestratorClient:
    return request.app.state.orchestrator_client


def get_pipeline_operations_service(
    orchestrator: Annotated[OrchestratorClient, Depends(get_orchestrator_client)],
) -> PipelineOperationsService:
    return PipelineOperationsService(orchestrator)
