from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from api.config import get_settings
from api.database import create_database_pool
from api.logging_config import configure_logging
from api.routes.health import router as health_router
from api.routes.incidents import router as incidents_router
from api.routes.metrics import router as metrics_router
from api.routes.schema_snapshots import router as schema_snapshots_router

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    pool = create_database_pool(settings)
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


app = FastAPI(
    title=settings.service_name,
    version=settings.version,
    description="API for Open DataOps Platform operational metadata.",
    lifespan=lifespan,
)
app.include_router(health_router)
app.include_router(incidents_router)
app.include_router(metrics_router)
app.include_router(schema_snapshots_router)
