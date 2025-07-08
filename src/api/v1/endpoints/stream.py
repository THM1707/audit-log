"""API endpoints for real-time log streaming."""

import logging

from fastapi import APIRouter, Depends, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import HTMLResponse

from src.core import config
from src.core.auth import get_current_user, role_required
from src.database.pool import get_db
from src.schemas import User, UserRole
from src.services.stream_service import StreamService

router = APIRouter(prefix="/logs")

settings = config.get_settings()
logger = logging.getLogger(__name__)


@router.websocket("/stream", dependencies=[Depends(role_required(UserRole.AUDITOR))])
async def stream_logs(
    websocket: WebSocket, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Websocket endpoint for streaming logs.

    Args:
        websocket (WebSocket): WebSocket connection
        db (AsyncSession): Database session
        current_user (User): Session user
    """
    try:
        stream_service = StreamService(db)
        await stream_service.stream_logs(current_user.tenant_id, websocket)
    except Exception as e:
        await websocket.close(code=1011, reason=str(e))
        logger.error(f"Error in stream_logs endpoint: {str(e)}")
        raise


@router.get("/board", dependencies=[Depends(role_required(UserRole.AUDITOR))])
async def board():
    """
    Real-time log streaming endpoint.
    Returns:
        HTMLResponse: A demo page for log streaming
    """
    html = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>Audit Log Stream</title>
            <style>
                body {
                    font-family: 'Courier New', monospace;
                    margin: 0;
                    padding: 20px;
                    background-color: #1e1e1e;
                    color: #e0e0e0;
                }
                h1 {
                    color: #4fc3f7;
                    border-bottom: 1px solid #333;
                    padding-bottom: 10px;
                }
                #logs {
                    list-style: none;
                    padding: 0;
                    margin: 0;
                }
                .log-entry {
                    background: #2d2d2d;
                    margin-bottom: 8px;
                    padding: 12px;
                    border-radius: 4px;
                    border-left: 4px solid #4fc3f7;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.2);
                }
                .timestamp {
                    color: #9e9e9e;
                    font-size: 0.85em;
                    margin-right: 10px;
                }
                .severity {
                    font-weight: bold;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-size: 0.8em;
                    text-transform: uppercase;
                    margin-right: 8px;
                }
                .severity.info { background: #2196f3; color: white; }
                .severity.warning { background: #ff9800; color: black; }
                .severity.error { background: #f44336; color: white; }
                .severity.debug { background: #9c27b0; color: white; }
                .action {
                    color: #4caf50;
                    font-weight: bold;
                }
                .message {
                    margin: 8px 0 0 0;
                    padding: 8px;
                    background: #252525;
                    border-radius: 3px;
                    white-space: pre-wrap;
                    word-break: break-word;
                }
                .metadata {
                    margin-top: 8px;
                    padding: 8px;
                    background: #1a1a1a;
                    border-radius: 3px;
                    font-size: 0.9em;
                    color: #b0bec5;
                    white-space: pre;
                    overflow-x: auto;
                }
            </style>
        </head>
        <body>
            <h1>Logs</h1>
            <ul id='logs'></ul>
            <script>
                var ws = new WebSocket("ws://localhost:8000/api/logs/stream");
                ws.onmessage = function(event) {
                    var logsList = document.getElementById('logs');
                    try {
                        // Check if it's a heartbeat message
                        if (event.data === 'Checking for new logs') {
                            return;  // Skip heartbeat messages
                        }

                        // Parse the JSON data
                        const logEntries = JSON.parse(event.data);

                        // Clear previous logs if needed
                        // logsList.innerHTML = '';

                        // Add each log entry
                        logEntries.forEach(entry => {
                            const logItem = document.createElement('li');
                            // Format the timestamp if it exists
                            const timestamp = entry.timestamp || entry.created_at || new Date().toISOString();
                            const formattedTime = new Date(timestamp).toLocaleString();

                            // Create a more structured log entry
                            logItem.innerHTML = `
                                <div class="log-entry">
                                    <span class="timestamp">[${formattedTime}]</span>
                                    <span class="severity ${entry.severity || 'info'}">${entry.severity?.toUpperCase() || 'INFO'}</span>
                                    <span class="action">${entry.action || 'Unknown action'}</span>
                                    <div class="message">${entry.message || 'No message'}</div>
                                    ${entry.log_metadata ? `<div class="metadata">${JSON.stringify(entry.log_metadata, null, 2)}</div>` : ''}
                                </div>
                            `;

                            // Add to the top of the list
                            logsList.insertBefore(logItem, logsList.firstChild);

                            // Limit the number of logs to show (optional)
                            if (logsList.children.length > 50) {
                                logsList.removeChild(logsList.lastChild);
                            }
                        });
                    } catch (error) {
                        console.error('Error processing message:', error, event.data);
                        const errorItem = document.createElement('li');
                        errorItem.textContent = `Error: ${error.message}`;
                        logsList.insertBefore(errorItem, logsList.firstChild);
                    }
                };
            </script>
        </body>
    </html>
    """
    return HTMLResponse(html)
