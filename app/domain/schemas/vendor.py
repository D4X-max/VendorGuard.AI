from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field
from app.models.all_models import VendorCriticalityTier


class VendorCreate(BaseModel):
    legal_name: str = Field(min_length=2, max_length=255)
    domain: str = Field(min_length=3, max_length=255)
    criticality_tier: VendorCriticalityTier = VendorCriticalityTier.MEDIUM
    stores_customer_data: bool = False
    access_production_systems: bool = False
    handles_payments: bool = False
    handles_phi_pii: bool = False
    # Set by service layer — not accepted from client
    tenant_id: Optional[UUID] = None
    overall_inherent_score: Optional[float] = None


class VendorUpdate(BaseModel):
    legal_name: Optional[str] = Field(None, min_length=2, max_length=255)
    domain: Optional[str] = None
    criticality_tier: Optional[VendorCriticalityTier] = None
    stores_customer_data: Optional[bool] = None
    access_production_systems: Optional[bool] = None
    handles_payments: Optional[bool] = None
    handles_phi_pii: Optional[bool] = None


class VendorContactCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: str
    phone_number: Optional[str] = None
    is_primary: bool = False


class VendorContactResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    vendor_id: UUID
    first_name: str
    last_name: str
    email: str
    phone_number: Optional[str]
    is_primary: bool
    created_at: datetime


class VendorResponse(BaseModel):
    model_config = {"from_attributes": True}
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


class PaginatedVendorResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[VendorResponse]