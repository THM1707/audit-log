import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.endpoints import logs, tenants
from src.core.config import get_settings
from src.database.pool import db_manager, get_db
from src.models import AuditLog

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
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

        logger.info("🎉 Application startup complete")

    except Exception as e:
        logger.error(f"💥 Startup failed: {e}")
        raise

    yield  # Application runs here

    # Shutdown
    logger.info("🛑 Application shutdown...")

    try:
        await db_manager.close_db()
        logger.info("✅ Application shutdown complete")

    except Exception as e:
        logger.error(f"💥 Shutdown error: {e}")


app = FastAPI(
    title="Audit Log API",
    description="API for managing audit logs with multi-tenant support",
    version="1.0.0",
    lifespan=lifespan
)

# # Add development middleware
# app.add_middleware(DevAuthMiddleware)

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
# api_router.include_router(search.router, tags=["Search"])
# api_router.include_router(stream.router, tags=["Stream"])
api_router.include_router(tenants.router, tags=["Tenants"])
# api_router.include_router(export.router, tags=["Export"])

# Include API router in the main app
app.include_router(api_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to Audit Log API"}


@app.get("/health")
async def health_check():
    """Application health check"""
    is_db_healthy = await db_manager.health_check()
    pool_status = db_manager.get_pool_status()

    return {
        "status": "healthy" if is_db_healthy else "unhealthy",
        "database": {
            "status": "connected" if is_db_healthy else "disconnected",
            "pool": pool_status
        },
        "version": "1.0.0"
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
                    "retention_interval": settings.LOG_RETENTION_DAYS
                }
            },
        }

    except Exception as e:
        logger.error(f"Error fetching metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch metrics")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
