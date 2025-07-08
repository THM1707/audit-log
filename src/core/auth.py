from fastapi import Depends, Header, HTTPException, status

from src.schemas import User, UserRole


def get_tenant_id(x_tenant_id=Header(..., alias="X-Tenant-Id")) -> int:
    """Extract tenant ID from request headers."""
    if not x_tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing tenant ID in headers")
    return int(x_tenant_id)


def get_current_user(
    user_id: str = Header(..., alias="X-User-Id"),
    x_tenant_id: str = Header(..., alias="X-Tenant-Id"),
    user_name: str = Header(..., alias="X-User-Name"),
    user_role: str = Header(..., alias="X-User-Role"),
) -> User:
    """Get current user from request headers."""
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing user ID in headers")

    try:
        # Convert the role string to UserRole enum
        role_enum = UserRole(user_role)
    except (KeyError, AttributeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid user role: {user_role}")

    return User(id=user_id, role=role_enum, name=user_name, tenant_id=int(x_tenant_id))


def role_required(role_name: UserRole):
    func_dict = {
        UserRole.ADMIN: admin_role_required,
        UserRole.USER: user_role_required,
        UserRole.AUDITOR: auditor_role_required,
    }
    return func_dict[role_name]


def admin_role_required(role: str = Header(..., alias="X-User-Role")):
    """Dependency to check if user has the required role."""

    if role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"Role {role} not authorized to access this resource"
        )


def user_role_required(role: str = Header(..., alias="X-User-Role")):
    """Dependency to check if user has the required role."""

    if role != UserRole.ADMIN.value and role != UserRole.USER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"Role {role} not authorized to access this resource"
        )


def auditor_role_required(role: str = Header(..., alias="X-User-Role")):
    """Dependency to check if user has the required role."""
    if role != UserRole.ADMIN.value and role != UserRole.AUDITOR.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"Role {role} not authorized to access this resource"
        )
