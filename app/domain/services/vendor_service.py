import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.vendor_repo import VendorRepository
from app.domain.schemas.vendor import VendorCreate, VendorUpdate, VendorResponse, PaginatedVendorResponse
from app.models.all_models import Vendor
from app.workers.audit_tasks import log_audit_event

logger = logging.getLogger(__name__)


class VendorService:
    """
    All vendor business logic lives here.
    No HTTP context. No FastAPI imports.
    Fully unit-testable with a mock session.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = VendorRepository(session)

    async def onboard_vendor(
        self, vendor_in: VendorCreate, user_id: UUID, tenant_id: UUID
    ) -> VendorResponse:
        # 1. Calculate inherent risk score
        score = self._calculate_inherent_risk(vendor_in)

        # 2. Build ORM object
        vendor = Vendor(
            tenant_id=tenant_id,
            legal_name=vendor_in.legal_name,
            domain=vendor_in.domain,
            criticality_tier=vendor_in.criticality_tier,
            stores_customer_data=vendor_in.stores_customer_data,
            access_production_systems=vendor_in.access_production_systems,
            handles_payments=vendor_in.handles_payments,
            handles_phi_pii=vendor_in.handles_phi_pii,
            overall_inherent_score=score,
        )

        # 3. Persist
        db_vendor = await self.repo.create(vendor)
        await self.session.commit()
        await self.session.refresh(db_vendor)

        # 4. Emit async audit event (non-blocking Celery task)
        try:
            log_audit_event.delay(
                tenant_id=str(tenant_id),
                user_id=str(user_id),
                action="VENDOR_ONBOARDED",
                entity_target="vendors",
                entity_id=str(db_vendor.id),
            )
        except Exception:
            logger.warning("Audit log skipped — Redis unavailable")

        logger.info(
            "Vendor onboarded",
            extra={"vendor_id": str(db_vendor.id), "tenant_id": str(tenant_id)},
        )
        return VendorResponse.model_validate(db_vendor)

    async def get_vendor(self, vendor_id: UUID, tenant_id: UUID) -> VendorResponse:
        vendor = await self.repo.get_by_id_for_tenant(vendor_id, tenant_id)
        if not vendor:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Vendor not found.")
        return VendorResponse.model_validate(vendor)

    async def list_vendors(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        criticality_filter: str = None,
    ) -> PaginatedVendorResponse:
        skip = (page - 1) * page_size
        vendors, total = await self.repo.get_all_for_tenant(
            tenant_id, skip=skip, limit=page_size,
            criticality_filter=criticality_filter,
        )
        return PaginatedVendorResponse(
            total=total,
            page=page,
            page_size=page_size,
            items=[VendorResponse.model_validate(v) for v in vendors],
        )

    async def update_vendor(
        self, vendor_id: UUID, tenant_id: UUID, data: VendorUpdate, user_id: UUID
    ) -> VendorResponse:
        vendor = await self.repo.get_by_id_for_tenant(vendor_id, tenant_id)
        if not vendor:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Vendor not found.")

        update_data = data.model_dump(exclude_none=True)
        updated = await self.repo.update_vendor(vendor_id, tenant_id, update_data)
        await self.session.commit()

        try:
            log_audit_event.delay(
                tenant_id=str(tenant_id),
                user_id=str(user_id),
                action="VENDOR_UPDATED",
                entity_target="vendors",
                entity_id=str(vendor_id),
            )
        except Exception:
            logger.warning("Audit log skipped — Redis unavailable")
        return VendorResponse.model_validate(updated)

    async def delete_vendor(
        self, vendor_id: UUID, tenant_id: UUID, user_id: UUID
    ) -> None:
        vendor = await self.repo.get_by_id_for_tenant(vendor_id, tenant_id)
        if not vendor:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Vendor not found.")

        await self.repo.delete(vendor_id)
        await self.session.commit()

        try:
            log_audit_event.delay(
                tenant_id=str(tenant_id),
                user_id=str(user_id),
                action="VENDOR_DELETED",
                entity_target="vendors",
                entity_id=str(vendor_id),
            )
        except Exception:
            logger.warning("Audit log skipped — Redis unavailable")

    def _calculate_inherent_risk(self, vendor: VendorCreate) -> float:
        score = 0.0
        if vendor.stores_customer_data:      score += 40.0
        if vendor.access_production_systems: score += 30.0
        if vendor.handles_payments:          score += 20.0
        if vendor.handles_phi_pii:           score += 10.0
        return score