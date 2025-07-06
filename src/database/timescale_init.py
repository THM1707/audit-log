"""TimescaleDB initialization and configuration."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncConnection

from src.core import config

settings = config.get_settings()


async def create_hypertable(conn: AsyncConnection):
    """
    Create TimescaleDB hypertable with multidimensional partitioning.
    """
    # Create hypertable
    await conn.execute(
        text("""
            SELECT create_hypertable(
                'audit_logs',
                'created_at',
                chunk_time_interval => INTERVAL '1 month',
                if_not_exists => TRUE
            );
        """)
    )

    # Add tenant_id as dimension
    await conn.execute(
        text("""
            SELECT add_dimension(
                'audit_logs',
                'tenant_id',
                number_partitions => 4,
                if_not_exists => TRUE
            );
        """)
    )


async def add_policies(conn: AsyncConnection):
    # Set compression settings
    await conn.execute(
        text(
            """
            ALTER TABLE audit_logs SET (
                timescaledb.compress = TRUE,
                timescaledb.compress_segmentby = 'tenant_id',
                timescaledb.compress_orderby = 'created_at DESC'
                );
            """
        )
    )

    # Then add the compression policy
    await conn.execute(
        text("""
            SELECT add_compression_policy(
                'audit_logs',
                INTERVAL '7 days',
                if_not_exists => TRUE
            );
        """)
    )

    # Set retention policy
    await conn.execute(
        text("""
            SELECT add_retention_policy(
                'audit_logs',
                INTERVAL '90 days',
                if_not_exists => TRUE
            );
        """)
    )


async def init_timescale(conn: AsyncConnection):
    """
    Initialize TimescaleDB with all configuration
    """

    await create_hypertable(conn)
    await add_policies(conn)
