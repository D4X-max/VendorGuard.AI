from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_tenant_session
from app.api.dependencies.auth import get_current_active_user, require_permissions
from app.domain.schemas.user import UserInDB
from app.domain.schemas.vendor import (
    VendorCreate, VendorUpdate, VendorResponse,
    VendorContactCreate, VendorContactResponse, PaginatedVendorResponse
)
from app.domain.services.vendor_service import VendorService

router = APIRouter(prefix="/vendors", tags=["Vendors"])


@router.get("", response_model=PaginatedVendorResponse)
async def list_vendors(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    criticality: Optional[str] = Query(default=None),
    current_user: UserInDB = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_tenant_session),
):
    service = VendorService(session)
    return await service.list_vendors(
        tenant_id=current_user.tenant_id,
        page=page,
        page_size=page_size,
        criticality_filter=criticality,
    )


@router.post("", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    vendor_in: VendorCreate,
    current_user: UserInDB = Depends(require_permissions(["vendor:write"])),
    session: AsyncSession = Depends(get_tenant_session),
):
    service = VendorService(session)
    return await service.onboard_vendor(
        vendor_in=vendor_in,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )


@router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(
    vendor_id: UUID,
    current_user: UserInDB = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_tenant_session),
):
    service = VendorService(session)
    return await service.get_vendor(vendor_id, current_user.tenant_id)


@router.patch("/{vendor_id}", response_model=VendorResponse)
async def update_vendor(
    vendor_id: UUID,
    body: VendorUpdate,
    current_user: UserInDB = Depends(require_permissions(["vendor:write"])),
    session: AsyncSession = Depends(get_tenant_session),
):
    service = VendorService(session)
    return await service.update_vendor(
        vendor_id=vendor_id,
        tenant_id=current_user.tenant_id,
        data=body,
        user_id=current_user.id,
    )


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vendor(
    vendor_id: UUID,
    current_user: UserInDB = Depends(require_permissions(["vendor:delete"])),
    session: AsyncSession = Depends(get_tenant_session),
):
    service = VendorService(session)
    await service.delete_vendor(
        vendor_id=vendor_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )