from fastapi import Request, Response
from starlette.datastructures import MutableHeaders
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Scope, Receive, Send

from src.core.config import get_settings
from src.schemas import UserRole

settings = get_settings()


async def mock_api_gateway_header(request: Request, call_next) -> Response:
    if settings.DEBUG:
        # Create a mutable copy of the headers
        headers = dict(request.headers)

        # Set mock user data
        mock_user = {
            "X-User-Id": "1",
            "X-User-Role": UserRole.ADMIN.value,  # Convert enum to string
            "X-User-Name": "Mock Admin",
            "X-Tenant-Id": "1"
        }

        # Update headers with mock data
        headers.update(mock_user)

        # Create a new request with updated headers
        request.scope["headers"] = [
            (k.lower().encode(), v.encode())
            for k, v in headers.items()
        ]

    response = await call_next(request)
    return response


class MockAPIGatewayASGIMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if settings.DEBUG and scope["type"] in ["http", "websocket"]:
            mock_user_headers = [
                (b"x-user-id", b"1"),
                (b"x-user-role", UserRole.ADMIN.value.encode()),
                (b"x-user-name", b"Mock Admin"),
                (b"x-tenant-id", b"1")
            ]

            # Add mock headers to existing headers
            scope["headers"] = scope.get("headers", []) + mock_user_headers

        await self.app(scope, receive, send)
