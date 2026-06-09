"""
Pydantic v2 schemas for request validation and response serialization.
Separated from ORM models — never expose ORM objects directly to API layer.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.models.all_models import (
    VendorCriticalityTier,
    FindingStatusType,
    QuestionnaireStatusType,
)


# ─────────────────────────────────────────────
# BASE
# ─────────────────────────────────────────────
class BaseResponse(BaseModel):
    model_config = {"from_attributes": True}


# =========================================================================
# AUTH SCHEMAS
# =========================================================================

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    refresh_token: str


class TenantRegisterRequest(BaseModel):
    tenant_name: str = Field(min_length=2, max_length=255)
    tenant_domain: str = Field(min_length=3, max_length=255)
    admin_email: EmailStr
    admin_password: str = Field(min_length=8)
    admin_first_name: str = Field(min_length=1, max_length=100)
    admin_last_name: str = Field(min_length=1, max_length=100)


# =========================================================================
# USER SCHEMAS
# =========================================================================

class UserResponse(BaseResponse):
    id: UUID
    tenant_id: UUID
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    is_active: bool
    mfa_enabled: bool
    created_at: datetime


# =========================================================================
# VENDOR SCHEMAS
# =========================================================================

class VendorCreateRequest(BaseModel):
    legal_name: str = Field(min_length=2, max_length=255)
    domain: str = Field(min_length=3, max_length=255)
    criticality_tier: VendorCriticalityTier = VendorCriticalityTier.MEDIUM
    stores_customer_data: bool = False
    access_production_systems: bool = False
    handles_payments: bool = False
    handles_phi_pii: bool = False


class VendorUpdateRequest(BaseModel):
    legal_name: Optional[str] = Field(None, min_length=2, max_length=255)
    domain: Optional[str] = None
    criticality_tier: Optional[VendorCriticalityTier] = None
    stores_customer_data: Optional[bool] = None
    access_production_systems: Optional[bool] = None
    handles_payments: Optional[bool] = None
    handles_phi_pii: Optional[bool] = None


class VendorResponse(BaseResponse):
    id: UUID
    tenant_id: UUID
    legal_name: str
    domain: str
    criticality_tier: VendorCriticalityTier
    stores_customer_data: bool
    access_production_systems: bool
    handles_payments: bool
    handles_phi_pii: bool
    overall_inherent_score: Optional[float]
    created_at: datetime
    updated_at: datetime


class VendorContactCreateRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone_number: Optional[str] = None
    is_primary: bool = False


class VendorContactResponse(BaseResponse):
    id: UUID
    vendor_id: UUID
    first_name: str
    last_name: str
    email: str
    phone_number: Optional[str]
    is_primary: bool
    created_at: datetime


# =========================================================================
# QUESTIONNAIRE SCHEMAS
# =========================================================================

class QuestionCreateRequest(BaseModel):
    control_code: Optional[str] = None
    question_text: str = Field(min_length=10)
    hint_text: Optional[str] = None
    weight: float = Field(default=1.00, ge=0.1, le=10.0)
    sequence_order: int = Field(ge=1)


class QuestionnaireCreateRequest(BaseModel):
    vendor_id: UUID
    title: str = Field(min_length=3, max_length=255)
    due_date: Optional[datetime] = None
    questions: List[QuestionCreateRequest] = Field(min_length=1)


class QuestionResponse(BaseResponse):
    id: UUID
    questionnaire_id: UUID
    control_code: Optional[str]
    question_text: str
    hint_text: Optional[str]
    weight: float
    sequence_order: int


class QuestionnaireResponse(BaseResponse):
    id: UUID
    tenant_id: UUID
    vendor_id: UUID
    title: str
    status: QuestionnaireStatusType
    assigned_analyst_id: Optional[UUID]
    due_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    questions: List[QuestionResponse] = []


class QuestionnaireStatusUpdateRequest(BaseModel):
    status: QuestionnaireStatusType


# =========================================================================
# FINDINGS SCHEMAS
# =========================================================================

class FindingCreateRequest(BaseModel):
    vendor_id: UUID
    questionnaire_id: Optional[UUID] = None
    control_id: Optional[UUID] = None
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=10)
    severity_level: str = Field(pattern="^(CRITICAL|HIGH|MEDIUM|LOW)$")
    source_document_id: Optional[UUID] = None
    source_page_number: Optional[int] = None
    extracted_evidence_chunk: Optional[str] = None
    ai_confidence_score: Optional[float] = Field(None, ge=0, le=100)
    ai_reasoning_rationale: Optional[str] = None


class FindingUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity_level: Optional[str] = Field(None, pattern="^(CRITICAL|HIGH|MEDIUM|LOW)$")
    status: Optional[FindingStatusType] = None


class FindingResponse(BaseResponse):
    id: UUID
    tenant_id: UUID
    vendor_id: UUID
    questionnaire_id: Optional[UUID]
    control_id: Optional[UUID]
    title: str
    description: str
    severity_level: str
    status: FindingStatusType
    source_document_id: Optional[UUID]
    source_page_number: Optional[int]
    extracted_evidence_chunk: Optional[str]
    ai_confidence_score: Optional[float]
    ai_reasoning_rationale: Optional[str]
    identified_at: datetime
    updated_at: datetime


# =========================================================================
# REMEDIATION SCHEMAS
# =========================================================================

class RemediationCreateRequest(BaseModel):
    action_plan: str = Field(min_length=10)
    target_resolution_date: datetime
    owner_user_id: Optional[UUID] = None


class RemediationResponse(BaseResponse):
    id: UUID
    finding_id: UUID
    action_plan: str
    target_resolution_date: datetime
    owner_user_id: Optional[UUID]
    status: str
    created_at: datetime
    updated_at: datetime


# =========================================================================
# PAGINATION
# =========================================================================

class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list