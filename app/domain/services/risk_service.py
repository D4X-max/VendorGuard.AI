from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.all_models import Vendor, Finding, RiskRegister, FindingStatusType
import logging
import uuid

logger = logging.getLogger(__name__)


class RiskService:
    """
    Quantitative Risk Scoring Engine.

    Formula:
        Residual Risk = min(100, Inherent Risk × (1 + ΣPenalties))

    Penalty Weights:
        CRITICAL = +0.50 (50% increase)
        HIGH     = +0.30 (30% increase)
        MEDIUM   = +0.10 (10% increase)
        LOW      = +0.00 (no increase)

    Risk Appetite Thresholds:
        <= 70 → WITHIN_APPETITE  → ACCEPT
        >  70 → EXCEEDS_APPETITE → MITIGATE
    """

    PENALTY_WEIGHTS = {
        "CRITICAL": 0.50,
        "HIGH":     0.30,
        "MEDIUM":   0.10,
        "LOW":      0.00,
    }

    RISK_APPETITE_THRESHOLD = 70.0

    def __init__(self, session: AsyncSession):
        self.session = session

    async def recalculate_residual_risk(
        self, tenant_id: str, vendor_id: str
    ) -> dict:
        """
        Full risk recalculation for a vendor.
        Called whenever a finding status changes.
        Returns a dict with full risk breakdown.
        """

        # 1. Fetch vendor inherent risk baseline
        vendor_result = await self.session.execute(
            select(Vendor).where(
                Vendor.id == uuid.UUID(vendor_id),
                Vendor.tenant_id == uuid.UUID(tenant_id),
            )
        )
        vendor_obj = vendor_result.scalar_one_or_none()
        if not vendor_obj:
            raise ValueError(f"Vendor {vendor_id} not found.")

        inherent_risk = float(vendor_obj.overall_inherent_score or 0)

        # 2. Fetch all APPROVED findings (active gaps)
        findings_result = await self.session.execute(
            select(Finding).where(
                Finding.vendor_id == uuid.UUID(vendor_id),
                Finding.tenant_id == uuid.UUID(tenant_id),
                Finding.status == FindingStatusType.APPROVED,
            )
        )
        active_findings = findings_result.scalars().all()

        # 3. Calculate penalty sum across all active findings
        penalty_breakdown = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        penalty_sum = 0.0

        for finding in active_findings:
            severity = finding.severity_level.upper()
            penalty = self.PENALTY_WEIGHTS.get(severity, 0.0)
            penalty_sum += penalty
            if severity in penalty_breakdown:
                penalty_breakdown[severity] += 1

        # 4. Apply quantitative formula — hard cap at 100
        raw_residual = inherent_risk * (1 + penalty_sum)
        residual_risk = round(min(100.0, raw_residual), 2)

        # 5. Determine risk appetite status and treatment strategy
        risk_appetite = (
            "WITHIN_APPETITE"
            if residual_risk <= self.RISK_APPETITE_THRESHOLD
            else "EXCEEDS_APPETITE"
        )
        treatment = "MITIGATE" if residual_risk > self.RISK_APPETITE_THRESHOLD else "ACCEPT"

        # 6. Upsert risk register
        await self._upsert_risk_register(
            tenant_id=tenant_id,
            vendor_id=vendor_id,
            inherent=inherent_risk,
            residual=residual_risk,
            risk_appetite=risk_appetite,
            treatment=treatment,
        )

        logger.info(
            f"Risk recalculated for vendor {vendor_id}",
            extra={
                "tenant_id": tenant_id,
                "inherent_risk": inherent_risk,
                "residual_risk": residual_risk,
                "penalty_sum": penalty_sum,
                "active_findings": len(active_findings),
            },
        )

        return {
            "inherent_risk": inherent_risk,
            "residual_risk": residual_risk,
            "penalty_sum": round(penalty_sum, 2),
            "active_findings_count": len(active_findings),
            "finding_breakdown": penalty_breakdown,
            "risk_appetite_status": risk_appetite,
            "treatment_strategy": treatment,
        }

    async def _upsert_risk_register(
        self,
        tenant_id: str,
        vendor_id: str,
        inherent: float,
        residual: float,
        risk_appetite: str,
        treatment: str,
    ) -> None:
        """
        Insert or update the risk_register entry for this vendor.
        Acts as a ledger — always reflects the latest calculated state.
        """
        result = await self.session.execute(
            select(RiskRegister).where(
                RiskRegister.vendor_id == uuid.UUID(vendor_id),
                RiskRegister.tenant_id == uuid.UUID(tenant_id),
            )
        )
        register_entry = result.scalar_one_or_none()

        # Next review date — 90 days for high risk, 180 days for within appetite
        days_until_review = 90 if residual > self.RISK_APPETITE_THRESHOLD else 180
        next_review = datetime.now(timezone.utc) + timedelta(days=days_until_review)

        if register_entry:
            # Update existing entry
            register_entry.inherent_risk_score = inherent
            register_entry.residual_risk_score = residual
            register_entry.risk_appetite_status = risk_appetite
            register_entry.treatment_strategy = treatment
            register_entry.next_review_date = next_review
            register_entry.updated_at = datetime.now(timezone.utc)
        else:
            # Create new entry
            new_entry = RiskRegister(
                tenant_id=uuid.UUID(tenant_id),
                vendor_id=uuid.UUID(vendor_id),
                inherent_risk_score=inherent,
                residual_risk_score=residual,
                risk_appetite_status=risk_appetite,
                treatment_strategy=treatment,
                next_review_date=next_review,
            )
            self.session.add(new_entry)

        await self.session.flush()