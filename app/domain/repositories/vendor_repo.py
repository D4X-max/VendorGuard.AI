from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.repositories.base import BaseRepository
from app.models.all_models import Vendor, VendorContact


class VendorRepository(BaseRepository[Vendor]):

    def __init__(self, session: AsyncSession):
        super().__init__(Vendor, session)

    async def get_by_id_for_tenant(
        self, vendor_id: UUID, tenant_id: UUID
    ) -> Optional[Vendor]:
        result = await self.session.execute(
            select(Vendor)
            .where(Vendor.id == vendor_id, Vendor.tenant_id == tenant_id)
            .options(selectinload(Vendor.contacts))
        )
        return result.scalar_one_or_none()

    async def get_all_for_tenant(
        self, tenant_id: UUID, skip: int = 0, limit: int = 20,
        criticality_filter: Optional[str] = None,
    ) -> tuple[List[Vendor], int]:
        base_filter = [Vendor.tenant_id == tenant_id]
        if criticality_filter:
            base_filter.append(Vendor.criticality_tier == criticality_filter)

        count_result = await self.session.execute(
            select(func.count()).select_from(Vendor).where(*base_filter)
        )
        total = count_result.scalar_one()

        result = await self.session.execute(
            select(Vendor)
            .where(*base_filter)
            .order_by(Vendor.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all(), total

    async def update_vendor(
        self, vendor_id: UUID, tenant_id: UUID, data: dict
    ) -> Optional[Vendor]:
        await self.session.execute(
            update(Vendor)
            .where(Vendor.id == vendor_id, Vendor.tenant_id == tenant_id)
            .values(**data)
        )
        await self.session.flush()
        return await self.get_by_id_for_tenant(vendor_id, tenant_id)

    async def add_contact(
        self, tenant_id: UUID, vendor_id: UUID, data: dict
    ) -> VendorContact:
        contact = VendorContact(tenant_id=tenant_id, vendor_id=vendor_id, **data)
        self.session.add(contact)
        await self.session.flush()
        return contact