from enum import Enum
from pydantic import BaseModel

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    AUDITOR = "auditor"

class User(BaseModel):
    """Schema representing a user authenticated via API Gateway."""
    
    id: str
    name: str
    role: UserRole
    tenant_id: str

    class Config:
        from_attributes = True
