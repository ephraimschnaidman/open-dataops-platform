from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI
from fastapi.openapi.utils import get_openapi

from api.auth_dependencies import require_roles
from api.config import Settings, get_settings
from api.database import create_database_pool
from api.logging_config import configure_logging
from api.orchestrators.airflow import AirflowClient, create_airflow_http_client
from api.routes.auth import router as auth_router
from api.routes.alerts import router as alerts_router
from api.routes.dbt_metadata import router as dbt_metadata_router
from api.routes.data_sources import router as data_sources_router
from api.routes.health import router as health_router
from api.routes.incidents import router as incidents_router
from api.routes.metrics import router as metrics_router
from api.routes.logs import router as logs_router
from api.routes.operations import router as operations_router
from api.routes.pipelines import router as pipelines_router
from api.routes.pipeline_runs import router as pipeline_runs_router
from api.routes.schema_snapshots import router as schema_snapshots_router
from api.routes.validation import router as validation_router
from api.routes.monitoring import router as monitoring_router
from api.routes.health_metrics import router as health_metrics_router
from api.routes.dashboard import router as dashboard_router

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

require_operational_access = require_roles(
    "Admin",
    "Operator",
    "ReadOnly",
)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    application_settings: Settings = application.state.settings
    pool = create_database_pool(application_settings)
    application.state.database_pool = pool
    airflow_http_client = create_airflow_http_client(application_settings)
    orchestrator_client = AirflowClient(airflow_http_client)
    application.state.airflow_http_client = airflow_http_client
    application.state.orchestrator_client = orchestrator_client
    logger.info("Opening database connection pool", extra={"event": "database_pool_opening"})
    await pool.open(wait=False)
    logger.info("Database connection pool opened", extra={"event": "database_pool_opened"})
    try:
        yield
    finally:
        logger.info("Closing orchestrator client", extra={"event": "orchestrator_client_closing"})
        await orchestrator_client.aclose()
        logger.info("Orchestrator client closed", extra={"event": "orchestrator_client_closed"})
        logger.info("Closing database connection pool", extra={"event": "database_pool_closing"})
        await pool.close()
        logger.info("Database connection pool closed", extra={"event": "database_pool_closed"})


def create_app(application_settings: Settings) -> FastAPI:
    documentation_enabled = application_settings.api_docs_enabled
    application = FastAPI(
        title=application_settings.service_name,
        version=application_settings.version,
        description="API for Open DataOps Platform operational metadata.",
        lifespan=lifespan,
        docs_url="/docs" if documentation_enabled else None,
        redoc_url="/redoc" if documentation_enabled else None,
        openapi_url="/openapi.json" if documentation_enabled else None,
    )
    application.state.settings = application_settings
    application.include_router(health_router)
    application.include_router(auth_router)
    operational_dependencies = [Depends(require_operational_access)]
    application.include_router(
        incidents_router,
        dependencies=operational_dependencies,
    )
    application.include_router(
        metrics_router,
        dependencies=operational_dependencies,
    )
    application.include_router(
        schema_snapshots_router,
        dependencies=operational_dependencies,
    )
    application.include_router(
        dbt_metadata_router,
        dependencies=operational_dependencies,
    )
    application.include_router(
        alerts_router,
        dependencies=operational_dependencies,
    )
    application.include_router(
        validation_router,
        dependencies=operational_dependencies,
    )
    application.include_router(
        logs_router,
        dependencies=operational_dependencies,
    )
    application.include_router(
        data_sources_router,
        dependencies=operational_dependencies,
    )
    application.include_router(
        pipelines_router,
        dependencies=operational_dependencies,
    )
    application.include_router(
        pipeline_runs_router,
        dependencies=operational_dependencies,
    )
    application.include_router(
        operations_router,
        dependencies=operational_dependencies,
    )
    application.include_router(
        monitoring_router,
        dependencies=operational_dependencies,
    )
    application.include_router(
        health_metrics_router,
        dependencies=operational_dependencies,
    )
    application.include_router(
        dashboard_router,
        dependencies=operational_dependencies,
    )

    def custom_openapi() -> dict:
        if application.openapi_schema:
            return application.openapi_schema
        schema = get_openapi(
            title=application.title,
            version=application.version,
            description=application.description,
            routes=application.routes,
        )
        security_schemes = schema.setdefault("components", {}).setdefault(
            "securitySchemes",
            {},
        )
        security_schemes.setdefault(
            "OAuth2PasswordBearer",
            {
                "type": "oauth2",
                "flows": {
                    "password": {
                        "tokenUrl": "/api/v1/auth/token",
                        "scopes": {},
                    }
                },
            },
        )
        application.openapi_schema = schema
        return schema

    application.openapi = custom_openapi
    return application


app = create_app(settings)
