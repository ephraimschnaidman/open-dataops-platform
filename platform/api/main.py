from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from api.config import Settings, get_settings
from api.database import create_database_pool
from api.logging_config import configure_logging
from api.routes.auth import router as auth_router
from api.routes.dbt_metadata import router as dbt_metadata_router
from api.routes.health import router as health_router
from api.routes.incidents import router as incidents_router
from api.routes.metrics import router as metrics_router
from api.routes.pipelines import router as pipelines_router
from api.routes.schema_snapshots import router as schema_snapshots_router

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    application_settings: Settings = application.state.settings
    pool = create_database_pool(application_settings)
    application.state.database_pool = pool
    logger.info("Opening database connection pool", extra={"event": "database_pool_opening"})
    await pool.open(wait=False)
    logger.info("Database connection pool opened", extra={"event": "database_pool_opened"})
    try:
        yield
    finally:
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
    application.include_router(incidents_router)
    application.include_router(metrics_router)
    application.include_router(schema_snapshots_router)
    application.include_router(dbt_metadata_router)
    application.include_router(pipelines_router)

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
