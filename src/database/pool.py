"""Database connection pool management."""

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine
from sqlalchemy.orm import sessionmaker

from src.database.timescale_init import init_timescale
from src.models import Base, Tenant

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AsyncDatabaseManager:
    def __init__(self):
        self.engine: AsyncEngine | None = None
        self.session_factory: sessionmaker | None = None

    async def init_connection(self, database_url: str, max_retries: int = 5, retry_delay: int = 2) -> None:
        """Initialize database connection pool with retry logic."""
        current_retry = 0

        while current_retry < max_retries:
            try:
                self.engine = create_async_engine(
                    database_url,
                    echo=False,
                    pool_size=5,
                    max_overflow=10,
                    pool_timeout=30,
                    pool_recycle=3600,
                    pool_pre_ping=True
                )
                self.session_factory = async_sessionmaker(
                    self.engine,
                    expire_on_commit=False
                )
                logger.info("Database connection pool initialized")
                return
            except Exception as e:
                logger.warning(f"Attempt {current_retry + 1}/{max_retries} failed: {e}")
                if current_retry < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                current_retry += 1

        logger.error(f"Failed to initialize database connection after {max_retries} attempts")
        raise ConnectionError("Failed to connect to database after multiple attempts")

    async def init_db(self):
        # Drop tables if exists
        await self.drop_table_if_exists_raw_sql("audit_logs")
        await self.drop_table_if_exists_raw_sql("tenants")

        # Create all tables and initialize TimescaleDB
        try:
            async with self.engine.begin() as conn:
                # Create base tables
                await conn.run_sync(Base.metadata.create_all)
                logger.info("Base tables created successfully")

                # Initialize TimescaleDB
                await init_timescale(conn)
                logger.info("TimescaleDB initialized successfully")
                # Log success
                logger.info("Database initialization completed successfully")

            await self.populate_dummy_tenants()

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    async def drop_table_if_exists_raw_sql(self, table_name: str):
        """
        Drops a table if it exists using raw SQL.

        Args:
            table_name: The name of the table to drop.
        """
        async with self.engine.begin() as conn:
            print(f"Attempting to drop table '{table_name}' if it exists using raw SQL...")
            await conn.execute(text(f"DROP TABLE IF EXISTS {table_name};"))
            print(f"Table '{table_name}' drop attempt complete.")

    async def close_db(self):
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")

    async def get_session(self):
        """Get database session"""
        if not self.session_factory:
            raise RuntimeError("Database not initialized")

        async with self.session_factory() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {e}")
                raise
            finally:
                await session.close()

    async def health_check(self):
        """Check database health"""
        try:
            async with self.session_factory() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def get_pool_status(self):
        """Get connection pool status"""
        if not self.engine:
            return {"status": "not_initialized"}

        pool = self.engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
        }

    async def populate_dummy_tenants(self):
        """Populate dummy tenants"""
        async with self.session_factory() as session:
            session.add_all([
                Tenant(name="Tenant 1", description="Dummy Tenant 1"),
                Tenant(name="Tenant 2", description="Dummy Tenant 2"),
                Tenant(name="Tenant 3", description="Dummy Tenant 3"),
            ])
            await session.commit()


# Global database manager
db_manager = AsyncDatabaseManager()


# Dependency for getting database session
async def get_db():
    """FastAPI dependency for database session"""
    async for session in db_manager.get_session():
        yield session
