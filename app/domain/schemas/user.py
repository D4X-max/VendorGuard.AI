from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class UserInDB(BaseModel):
    """
    Represents the authenticated user extracted from JWT.
    Passed through FastAPI dependencies to service layer.
    """
    model_config = {"from_attributes": True}

    id: UUID
    tenant_id: UUID
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    is_active: bool
    mfa_enabled: bool
    permissions: List[str] = []  # Populated by get_current_user dependency


class TenantRegisterRequest(BaseModel):
    tenant_name: str = Field(min_length=2, max_length=255)
    tenant_domain: str = Field(min_length=3, max_length=255)
    admin_email: EmailStr
    admin_password: str = Field(min_length=8)
    admin_first_name: str = Field(min_length=1, max_length=100)
    admin_last_name: str = Field(min_length=1, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    is_active: bool
    mfa_enabled: bool
    created_at: datetime