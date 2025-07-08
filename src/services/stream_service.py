"""Service layer for real-time log streaming."""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Sequence

from fastapi.websockets import WebSocket, WebSocketDisconnect
from sqlalchemy import Row, RowMapping, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import AuditLog

logger = logging.getLogger(__name__)


class StreamService:
    """Service class for handling real-time log streaming."""

    def __init__(self, db: AsyncSession):
        """
        Initialize the StreamService.

        Args:
            db (AsyncSession): Async database session
        """
        self.db = db
        self.last_check_time = datetime.now(timezone.utc)
        self.check_interval = 10  # seconds

    async def get_new_logs_mapping(self, tenant_id: int) -> list[dict]:
        """
        Get new logs since last check.

        Args:
            tenant_id (int): ID of the tenant

        Returns:
            List[dict]: List of new audit logs as dictionaries
        """
        try:
            now = datetime.now(timezone.utc)
            time_window = now - timedelta(seconds=self.check_interval)

            # Get new logs
            query = (
                select(AuditLog)
                .where(AuditLog.tenant_id == tenant_id, AuditLog.created_at >= time_window)
                .order_by(AuditLog.created_at)
            )

            result = await self.db.execute(query)
            logs = result.scalars().all()

            # Convert SQLAlchemy objects to dictionaries and handle datetime serialization
            logs_data = []
            for log in logs:
                log_dict = {
                    "id": log.id,
                    "tenant_id": log.tenant_id,
                    "user_id": log.user_id,
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "message": log.message,
                    "before_state": log.before_state,
                    "after_state": log.after_state,
                    "log_metadata": log.log_metadata,
                    "severity": log.severity,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                    "updated_at": log.updated_at.isoformat() if log.updated_at else None,
                }
                logs_data.append(log_dict)

            # Update last check time
            self.last_check_time = now

            logger.info(f"Found {len(logs_data)} new logs for tenant {tenant_id}")
            return logs_data

        except Exception as e:
            logger.error(f"Error getting new logs: {str(e)}")
            raise

    async def stream_logs(self, tenant_id: int, websocket: WebSocket):
        """
        Stream logs in real-time to a WebSocket connection.

        Args:
            tenant_id (int): ID of the tenant
            websocket (WebSocket): WebSocket connection
        """
        try:
            await websocket.accept()

            while True:
                # Wait for new logs
                new_logs_mapping = await self.get_new_logs_mapping(tenant_id)

                if new_logs_mapping:
                    # Send logs to the client (already serialized as a list of dicts)
                    await websocket.send_text(json.dumps(new_logs_mapping))
                else:
                    # Send a heartbeat message
                    await websocket.send_text("Checking for new logs")

                # Wait for a short period before checking again
                await asyncio.sleep(self.check_interval)

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for tenant {tenant_id}")
        except Exception as e:
            logger.error(f"Error in stream_logs: {str(e)}")
            raise
