from fastapi import HTTPException, status, Request

from src.schemas import User, UserRole


def get_user_role(request: Request) -> UserRole:
    """Extract user role from request headers."""
    role = request.headers.get("X-User-Role")
    if not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing user role in headers"
        )
    try:
        return UserRole(role.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid user role: {role}"
        )


def get_tenant_id(request: Request) -> str:
    """Extract tenant ID from request headers."""
    tenant_id = request.headers.get("X-Tenant-Id")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing tenant ID in headers"
        )
    return tenant_id


def get_current_user(request: Request) -> User:
    """Get current user from request headers."""
    role = get_user_role(request)
    tenant_id = get_tenant_id(request)
    user_id = request.headers.get("X-User-Id")
    user_name = request.headers.get("X-User-Name")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing user ID in headers"
        )

    return User(
        id=user_id,
        role=role,
        name=user_name,
        tenant_id=tenant_id
    )


def require_role(required_role: UserRole):
    """Decorator to require a specific role."""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Request object not found"
                )

            user = get_current_user(request)
            if user.role != required_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role {user.role} not authorized to access this resource"
                )
            return await func(*args, **kwargs)

        return wrapper

    return decorator
