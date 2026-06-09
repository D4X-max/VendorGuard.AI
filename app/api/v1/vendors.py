from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, AuthenticatedUser
from app.repositories.repositories import VendorRepository, AuditRepository
from app.schemas.schemas import (
    VendorCreateRequest, VendorUpdateRequest, VendorResponse,
    VendorContactCreateRequest, VendorContactResponse, PaginatedResponse
)

router = APIRouter(prefix="/vendors", tags=["Vendors"])


@router.get("", response_model=PaginatedResponse)
async def list_vendors(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    skip = (page - 1) * page_size
    vendors, total = await VendorRepository.get_all(
        db, current_user.tenant_id, skip=skip, limit=page_size
    )
    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[VendorResponse.model_validate(v) for v in vendors],
    )


@router.post("", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    body: VendorCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await VendorRepository.create(
        db, current_user.tenant_id, body.model_dump()
    )

    # Compute inherent score based on risk flags
    score = sum([
        30 if vendor.stores_customer_data else 0,
        25 if vendor.access_production_systems else 0,
        25 if vendor.handles_payments else 0,
        20 if vendor.handles_phi_pii else 0,
    ])
    await VendorRepository.update(db, vendor.id, current_user.tenant_id, {"overall_inherent_score": score})

    await AuditRepository.log(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        user_email=current_user.email,
        action="VENDOR_CREATED",
        entity_target="vendors",
        entity_id=vendor.id,
        client_ip="0.0.0.0",
        user_agent="api",
        after=body.model_dump(),
    )

    return VendorResponse.model_validate(vendor)


@router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(
    vendor_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await VendorRepository.get_by_id(db, vendor_id, current_user.tenant_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found.")
    return VendorResponse.model_validate(vendor)


@router.patch("/{vendor_id}", response_model=VendorResponse)
async def update_vendor(
    vendor_id: UUID,
    body: VendorUpdateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await VendorRepository.get_by_id(db, vendor_id, current_user.tenant_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found.")

    update_data = body.model_dump(exclude_none=True)
    updated = await VendorRepository.update(db, vendor_id, current_user.tenant_id, update_data)

    await AuditRepository.log(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        user_email=current_user.email,
        action="VENDOR_UPDATED",
        entity_target="vendors",
        entity_id=vendor_id,
        client_ip="0.0.0.0",
        user_agent="api",
        after=update_data,
    )

    return VendorResponse.model_validate(updated)


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vendor(
    vendor_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deleted = await VendorRepository.delete(db, vendor_id, current_user.tenant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Vendor not found.")


@router.post("/{vendor_id}/contacts", response_model=VendorContactResponse, status_code=status.HTTP_201_CREATED)
async def add_vendor_contact(
    vendor_id: UUID,
    body: VendorContactCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await VendorRepository.get_by_id(db, vendor_id, current_user.tenant_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found.")

    contact = await VendorRepository.add_contact(
        db, current_user.tenant_id, vendor_id, body.model_dump()
    )
    return VendorContactResponse.model_validate(contact)