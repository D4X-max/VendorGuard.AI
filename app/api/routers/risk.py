from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.dependencies.database import get_tenant_session
from app.api.dependencies.auth import require_permissions, get_current_active_user
from app.domain.schemas.user import UserInDB
from app.domain.services.risk_service import RiskService
from app.models.all_models import RiskRegister, Finding, FindingStatusType

router = APIRouter(prefix="/risk", tags=["Risk Management"])


@router.patch("/findings/{finding_id}/approve")
async def approve_finding(
    finding_id: UUID,
    current_user: UserInDB = Depends(require_permissions(["risk:write"])),
    session: AsyncSession = Depends(get_tenant_session),
):
    """
    Analyst approves an AI-drafted finding.
    Automatically triggers full risk recalculation for the vendor.
    This is the core event-driven trigger of the risk engine.
    """
    # 1. Fetch and validate finding
    finding = await session.get(Finding, finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")

    if finding.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Finding not found.")

    if finding.status == FindingStatusType.APPROVED:
        raise HTTPException(
            status_code=400,
            detail="Finding is already approved.",
        )

    # 2. Approve the finding
    finding.status = FindingStatusType.APPROVED
    await session.flush()

    # 3. Trigger risk recalculation
    risk_service = RiskService(session)
    risk_result = await risk_service.recalculate_residual_risk(
        tenant_id=str(current_user.tenant_id),
        vendor_id=str(finding.vendor_id),
    )

    await session.commit()

    return {
        "message": "Finding approved. Risk register updated.",
        "finding_id": str(finding_id),
        "vendor_id": str(finding.vendor_id),
        **risk_result,
    }


@router.patch("/findings/{finding_id}/reject")
async def reject_finding(
    finding_id: UUID,
    current_user: UserInDB = Depends(require_permissions(["risk:write"])),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Rejects an AI-drafted finding and recalculates risk."""
    finding = await session.get(Finding, finding_id)
    if not finding or finding.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Finding not found.")

    finding.status = FindingStatusType.REJECTED
    await session.flush()

    # Recalculate — rejected finding no longer counts toward penalty
    risk_service = RiskService(session)
    risk_result = await risk_service.recalculate_residual_risk(
        tenant_id=str(current_user.tenant_id),
        vendor_id=str(finding.vendor_id),
    )

    await session.commit()

    return {
        "message": "Finding rejected. Risk register updated.",
        "finding_id": str(finding_id),
        **risk_result,
    }


@router.post("/vendor/{vendor_id}/recalculate")
async def trigger_recalculation(
    vendor_id: UUID,
    current_user: UserInDB = Depends(require_permissions(["risk:write"])),
    session: AsyncSession = Depends(get_tenant_session),
):
    """
    Manually trigger a full risk recalculation for a vendor.
    Useful after bulk finding updates or remediation completions.
    """
    risk_service = RiskService(session)
    try:
        risk_result = await risk_service.recalculate_residual_risk(
            tenant_id=str(current_user.tenant_id),
            vendor_id=str(vendor_id),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    await session.commit()
    return risk_result


@router.get("/register/vendor/{vendor_id}")
async def get_vendor_risk_profile(
    vendor_id: UUID,
    current_user: UserInDB = Depends(require_permissions(["risk:read"])),
    session: AsyncSession = Depends(get_tenant_session),
):
    """
    Returns the current risk register entry for a vendor.
    Used by the CISO dashboard to view live risk posture.
    """
    result = await session.execute(
        select(RiskRegister).where(
            RiskRegister.vendor_id == vendor_id,
            RiskRegister.tenant_id == current_user.tenant_id,
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(
            status_code=404,
            detail="No risk profile established for this vendor yet. Approve a finding to trigger calculation.",
        )

    return {
        "vendor_id": str(entry.vendor_id),
        "inherent_risk_score": float(entry.inherent_risk_score),
        "residual_risk_score": float(entry.residual_risk_score),
        "risk_appetite_status": entry.risk_appetite_status,
        "treatment_strategy": entry.treatment_strategy,
        "next_review_date": entry.next_review_date,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
    }


@router.get("/register/summary")
async def get_risk_summary(
    current_user: UserInDB = Depends(require_permissions(["risk:read"])),
    session: AsyncSession = Depends(get_tenant_session),
):
    """
    Portfolio-level risk summary for the CISO dashboard.
    Returns all vendors and their current risk posture.
    """
    result = await session.execute(
        select(RiskRegister).where(
            RiskRegister.tenant_id == current_user.tenant_id,
        ).order_by(RiskRegister.residual_risk_score.desc())
    )
    entries = result.scalars().all()

    total = len(entries)
    exceeds = sum(1 for e in entries if e.risk_appetite_status == "EXCEEDS_APPETITE")
    within = total - exceeds

    return {
        "total_vendors_assessed": total,
        "exceeds_appetite": exceeds,
        "within_appetite": within,
        "vendors": [
            {
                "vendor_id": str(e.vendor_id),
                "inherent_risk_score": float(e.inherent_risk_score),
                "residual_risk_score": float(e.residual_risk_score),
                "risk_appetite_status": e.risk_appetite_status,
                "treatment_strategy": e.treatment_strategy,
                "next_review_date": e.next_review_date,
            }
            for e in entries
        ],
    }