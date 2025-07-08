import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy import func, select
from starlette import status
from starlette.exceptions import HTTPException

from src.schemas.response import ErrorDetail, ErrorResponse

# Add the project root to the Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.endpoints import logs, search, stream, tenants
from src.core.config import get_settings
from src.database.pool import db_manager, get_db
from src.middleware.dev_auth import MockAPIGatewayASGIMiddleware
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


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handles FastAPI's HTTPException (e.g., 404, 401, 403, 413).
    These are "expected" HTTP errors.
    """
    error_detail = ErrorDetail(message=exc.detail, code=f"HTTP_{exc.status_code}")
    error_response = ErrorResponse(
        status="error",
        message=f"Request failed with HTTP status code {exc.status_code}",
        errors=[error_detail],
        code=str(exc.status_code),
    )
    return JSONResponse(status_code=exc.status_code, content=error_response.model_dump())


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """
    Handles Pydantic validation errors (often results in 422 Unprocessable Entity).
    """
    errors = []
    for error in exc.errors():
        errors.append(
            ErrorDetail(
                field=".".join(error["loc"]) if error["loc"] else None, message=error["msg"], code=error["type"]
            )
        )
    error_response = ErrorResponse(
        status="error", message="Validation error occurred.", errors=errors, code="VALIDATION_ERROR"
    )
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=error_response.model_dump())


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Handles all other unhandled exceptions (resulting in 500 Internal Server Error).
    This is your catch-all for unexpected issues.
    """
    # Log the full traceback for debugging (critical for 500 errors)
    logger.exception(f"Unhandled exception during request to {request.url}:")

    # In production, DO NOT expose the raw exception message or traceback to the client.
    # Provide a generic, user-friendly message.
    error_detail = ErrorDetail(
        message="An unexpected server error occurred. Please try again later.", code="INTERNAL_SERVER_ERROR"
    )
    error_response = ErrorResponse(
        status="error",
        message="An internal server error prevented the request from completing.",
        errors=[error_detail],
        code="500",
    )
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=error_response.model_dump())


@app.get("/", tags=["Mics"])
async def health_check():
    """Application health check"""
    is_db_healthy = await db_manager.health_check()
    pool_status = db_manager.get_pool_status()

    return {
        "status": "healthy" if is_db_healthy else "unhealthy",
        "database": {"status": "connected" if is_db_healthy else "disconnected", "pool": pool_status},
        "version": "1.0.0",
    }


@app.get("/metrics", tags=["Mics"])
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
