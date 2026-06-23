from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.repositories.base import BaseRepository
from app.models.all_models import User, Tenant


class UserRepository(BaseRepository[User]):

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(
            select(User)
            .where(User.email == email, User.is_active == True)
        )
        return result.scalar_one_or_none()

    async def get_by_email_and_tenant(
        self, email: str, tenant_id: UUID
    ) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(
                User.email == email,
                User.tenant_id == tenant_id,
                User.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def get_with_roles(self, user_id: UUID) -> Optional[User]:
        result = await self.session.execute(
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.roles)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()


class TenantRepository(BaseRepository[Tenant]):

    def __init__(self, session: AsyncSession):
        super().__init__(Tenant, session)

    async def get_by_domain(self, domain: str) -> Optional[Tenant]:
        result = await self.session.execute(
            select(Tenant).where(Tenant.domain == domain)
        )
        return result.scalar_one_or_none()