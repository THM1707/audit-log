import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy import func, select

# Add the project root to the Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.endpoints import logs, search, stream, tenants
from src.core.config import get_settings
from src.database.pool import db_manager, get_db
from src.middleware.dev_auth import MockAPIGatewayASGIMiddleware, mock_api_gateway_header
from src.models import AuditLog

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """FastAPI lifespan context manager"""
    # Startup
    logger.info("🚀 Application startup...")

    try:
        # Initialize database
        await db_manager.init_connection(settings.DATABASE_URL)
        await db_manager.init_db()

        # Run initial health check
        is_healthy = await db_manager.health_check()
        if is_healthy:
            logger.info("✅ Database connection established")
        else:
            logger.error("❌ Database connection failed")
            raise RuntimeError("Database initialization failed")

        logger.info("✅ Background worker started")

        logger.info("🎉 Application startup complete")

    except Exception as e:
        logger.error(f"💥 Startup failed: {e}")
        raise

    yield  # Application runs here

    # Shutdown
    logger.info("🛑 Application shutdown...")

    try:
        # Stop background worker
        logger.info("✅ Background worker stopped")

        # Close database connection
        await db_manager.close_db()
        logger.info("✅ Database connection closed")

        logger.info("✨ Application shutdown complete")

    except Exception as e:
        logger.error(f"💥 Shutdown error: {e}")


app = FastAPI(
    title="Audit Log API",
    description="API for managing audit logs with multi-tenant support",
    version="1.0.0",
    lifespan=lifespan,
)

# # Add development middleware
# app.middleware("http")(mock_api_gateway_header)
# app.middleware("websocket")(mock_api_gateway_header)
app.add_middleware(MockAPIGatewayASGIMiddleware)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create API router with /api prefix
api_router = APIRouter(prefix="/api")

# Include API routers
api_router.include_router(logs.router, tags=["Logs"])
api_router.include_router(search.router, tags=["Search"])
api_router.include_router(stream.router, tags=["Stream"])
api_router.include_router(tenants.router, tags=["Tenants"])
# api_router.include_router(export.router, tags=["Export"])

# Include API router in the main app
app.include_router(api_router)


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    logger.error(f"Validation error in {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": [{"loc": error["loc"], "msg": error["msg"], "type": error["type"]} for error in exc.errors()]
        },
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI request validation errors."""
    logger.error(f"Request validation error in {request.url.path}: {exc.errors()}")
    return JSONResponse(status_code=422, content={"detail": exc.errors(), "body": exc.body})


@app.get("/")
async def health_check():
    """Application health check"""
    is_db_healthy = await db_manager.health_check()
    pool_status = db_manager.get_pool_status()

    return {
        "status": "healthy" if is_db_healthy else "unhealthy",
        "database": {"status": "connected" if is_db_healthy else "disconnected", "pool": pool_status},
        "version": "1.0.0",
    }


@app.get("/metrics")
async def metrics(db: AsyncSession = Depends(get_db)):
    """Get service metrics."""

    try:
        # Get database metrics
        total_logs = await db.scalar(select(func.count(AuditLog.id)))
        # todo: get archived log

        # Get service metrics
        return {
            "database": {
                "total_logs": total_logs,
                "timescale": {
                    "compression_interval": settings.LOG_COMPRESSION_INTERVAL,
                    "retention_interval": settings.LOG_RETENTION_DAYS,
                },
            },
        }

    except Exception as e:
        logger.error(f"Error fetching metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch metrics")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
