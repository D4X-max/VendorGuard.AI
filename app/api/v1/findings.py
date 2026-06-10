from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user as get_current_user
from app.api.dependencies.database import get_tenant_session as get_db
from app.domain.schemas.user import UserInDB as AuthenticatedUser
from app.repositories.repositories import FindingRepository, VendorRepository, AuditRepository
from app.schemas.schemas import (
    FindingCreateRequest, FindingUpdateRequest, FindingResponse,
    RemediationCreateRequest, RemediationResponse, PaginatedResponse
)

router = APIRouter(prefix="/findings", tags=["Findings"])


@router.get("/vendor/{vendor_id}", response_model=PaginatedResponse)
async def list_findings(
    vendor_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await VendorRepository.get_by_id(db, vendor_id, current_user.tenant_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found.")

    skip = (page - 1) * page_size
    findings, total = await FindingRepository.get_all_by_vendor(
        db, current_user.tenant_id, vendor_id, skip=skip, limit=page_size
    )
    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[FindingResponse.model_validate(f) for f in findings],
    )


@router.post("", response_model=FindingResponse, status_code=status.HTTP_201_CREATED)
async def create_finding(
    body: FindingCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vendor = await VendorRepository.get_by_id(db, body.vendor_id, current_user.tenant_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found.")

    finding = await FindingRepository.create(
        db, current_user.tenant_id, body.model_dump()
    )

    await AuditRepository.log(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        user_email=current_user.email,
        action="FINDING_CREATED",
        entity_target="findings",
        entity_id=finding.id,
        client_ip="0.0.0.0",
        user_agent="api",
        after={"severity": body.severity_level, "title": body.title},
    )

    return FindingResponse.model_validate(finding)


@router.get("/{finding_id}", response_model=FindingResponse)
async def get_finding(
    finding_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    finding = await FindingRepository.get_by_id(db, finding_id, current_user.tenant_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")
    return FindingResponse.model_validate(finding)


@router.patch("/{finding_id}", response_model=FindingResponse)
async def update_finding(
    finding_id: UUID,
    body: FindingUpdateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    finding = await FindingRepository.get_by_id(db, finding_id, current_user.tenant_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")

    update_data = body.model_dump(exclude_none=True)
    updated = await FindingRepository.update(
        db, finding_id, current_user.tenant_id, update_data
    )
    return FindingResponse.model_validate(updated)


@router.post("/{finding_id}/remediation", response_model=RemediationResponse, status_code=status.HTTP_201_CREATED)
async def create_remediation(
    finding_id: UUID,
    body: RemediationCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    finding = await FindingRepository.get_by_id(db, finding_id, current_user.tenant_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")

    remediation = await FindingRepository.add_remediation(
        db, current_user.tenant_id, finding_id, body.model_dump()
    )
    return RemediationResponse.model_validate(remediation)