"""
Repository Layer — all raw DB operations live here.
No business logic. No HTTP concerns.
Routes and services call repositories; repositories call SQLAlchemy.
"""

import uuid
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload

from app.models.all_models import (
    Tenant, User, Vendor, VendorContact,
    Questionnaire, Question, Finding, Remediation,
    AuditLog, AIUsageLog,
)
from app.core.security import hash_password


# =========================================================================
# TENANT REPOSITORY
# =========================================================================

class TenantRepository:

    @staticmethod
    async def get_by_domain(session: AsyncSession, domain: str) -> Optional[Tenant]:
        result = await session.execute(
            select(Tenant).where(Tenant.domain == domain)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(session: AsyncSession, name: str, domain: str) -> Tenant:
        tenant = Tenant(name=name, domain=domain)
        session.add(tenant)
        await session.flush()
        return tenant


# =========================================================================
# USER REPOSITORY
# =========================================================================

class UserRepository:

    @staticmethod
    async def get_by_id(session: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_email(
        session: AsyncSession, tenant_id: uuid.UUID, email: str
    ) -> Optional[User]:
        result = await session.execute(
            select(User).where(
                User.tenant_id == tenant_id,
                User.email == email,
                User.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        session: AsyncSession,
        tenant_id: uuid.UUID,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        organization_id: Optional[uuid.UUID] = None,
    ) -> User:
        user = User(
            tenant_id=tenant_id,
            organization_id=organization_id,
            email=email,
            password_hash=hash_password(password),
            first_name=first_name,
            last_name=last_name,
        )
        session.add(user)
        await session.flush()
        return user


# =========================================================================
# VENDOR REPOSITORY
# =========================================================================

class VendorRepository:

    @staticmethod
    async def get_all(
        session: AsyncSession,
        tenant_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[List[Vendor], int]:
        # Count query
        count_result = await session.execute(
            select(func.count()).select_from(Vendor).where(
                Vendor.tenant_id == tenant_id
            )
        )
        total = count_result.scalar_one()

        # Data query
        result = await session.execute(
            select(Vendor)
            .where(Vendor.tenant_id == tenant_id)
            .order_by(Vendor.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all(), total

    @staticmethod
    async def get_by_id(
        session: AsyncSession, vendor_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[Vendor]:
        result = await session.execute(
            select(Vendor).where(
                Vendor.id == vendor_id,
                Vendor.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        session: AsyncSession, tenant_id: uuid.UUID, data: dict
    ) -> Vendor:
        vendor = Vendor(tenant_id=tenant_id, **data)
        session.add(vendor)
        await session.flush()
        return vendor

    @staticmethod
    async def update(
        session: AsyncSession,
        vendor_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: dict,
    ) -> Optional[Vendor]:
        await session.execute(
            update(Vendor)
            .where(Vendor.id == vendor_id, Vendor.tenant_id == tenant_id)
            .values(**data)
        )
        await session.flush()
        return await VendorRepository.get_by_id(session, vendor_id, tenant_id)

    @staticmethod
    async def delete(
        session: AsyncSession, vendor_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> bool:
        vendor = await VendorRepository.get_by_id(session, vendor_id, tenant_id)
        if not vendor:
            return False
        await session.delete(vendor)
        await session.flush()
        return True

    @staticmethod
    async def add_contact(
        session: AsyncSession, tenant_id: uuid.UUID, vendor_id: uuid.UUID, data: dict
    ) -> VendorContact:
        contact = VendorContact(tenant_id=tenant_id, vendor_id=vendor_id, **data)
        session.add(contact)
        await session.flush()
        return contact


# =========================================================================
# QUESTIONNAIRE REPOSITORY
# =========================================================================

class QuestionnaireRepository:

    @staticmethod
    async def get_all_by_vendor(
        session: AsyncSession, tenant_id: uuid.UUID, vendor_id: uuid.UUID
    ) -> List[Questionnaire]:
        result = await session.execute(
            select(Questionnaire)
            .where(
                Questionnaire.tenant_id == tenant_id,
                Questionnaire.vendor_id == vendor_id,
            )
            .options(selectinload(Questionnaire.questions))
            .order_by(Questionnaire.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_by_id(
        session: AsyncSession, questionnaire_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[Questionnaire]:
        result = await session.execute(
            select(Questionnaire)
            .where(
                Questionnaire.id == questionnaire_id,
                Questionnaire.tenant_id == tenant_id,
            )
            .options(selectinload(Questionnaire.questions))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        session: AsyncSession,
        tenant_id: uuid.UUID,
        vendor_id: uuid.UUID,
        title: str,
        due_date,
        questions_data: list,
        analyst_id: uuid.UUID,
    ) -> Questionnaire:
        questionnaire = Questionnaire(
            tenant_id=tenant_id,
            vendor_id=vendor_id,
            title=title,
            due_date=due_date,
            assigned_analyst_id=analyst_id,
        )
        session.add(questionnaire)
        await session.flush()

        for q in questions_data:
            question = Question(
                tenant_id=tenant_id,
                questionnaire_id=questionnaire.id,
                **q,
            )
            session.add(question)

        await session.flush()
        return questionnaire

    @staticmethod
    async def update_status(
        session: AsyncSession,
        questionnaire_id: uuid.UUID,
        tenant_id: uuid.UUID,
        status,
    ) -> Optional[Questionnaire]:
        await session.execute(
            update(Questionnaire)
            .where(
                Questionnaire.id == questionnaire_id,
                Questionnaire.tenant_id == tenant_id,
            )
            .values(status=status)
        )
        await session.flush()
        return await QuestionnaireRepository.get_by_id(session, questionnaire_id, tenant_id)


# =========================================================================
# FINDINGS REPOSITORY
# =========================================================================

class FindingRepository:

    @staticmethod
    async def get_all_by_vendor(
        session: AsyncSession,
        tenant_id: uuid.UUID,
        vendor_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[List[Finding], int]:
        count_result = await session.execute(
            select(func.count()).select_from(Finding).where(
                Finding.tenant_id == tenant_id,
                Finding.vendor_id == vendor_id,
            )
        )
        total = count_result.scalar_one()

        result = await session.execute(
            select(Finding)
            .where(Finding.tenant_id == tenant_id, Finding.vendor_id == vendor_id)
            .order_by(Finding.identified_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all(), total

    @staticmethod
    async def get_by_id(
        session: AsyncSession, finding_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[Finding]:
        result = await session.execute(
            select(Finding).where(
                Finding.id == finding_id,
                Finding.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        session: AsyncSession, tenant_id: uuid.UUID, data: dict
    ) -> Finding:
        finding = Finding(tenant_id=tenant_id, **data)
        session.add(finding)
        await session.flush()
        return finding

    @staticmethod
    async def update(
        session: AsyncSession,
        finding_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: dict,
    ) -> Optional[Finding]:
        await session.execute(
            update(Finding)
            .where(Finding.id == finding_id, Finding.tenant_id == tenant_id)
            .values(**data)
        )
        await session.flush()
        return await FindingRepository.get_by_id(session, finding_id, tenant_id)

    @staticmethod
    async def add_remediation(
        session: AsyncSession,
        tenant_id: uuid.UUID,
        finding_id: uuid.UUID,
        data: dict,
    ) -> Remediation:
        remediation = Remediation(
            tenant_id=tenant_id,
            finding_id=finding_id,
            **data,
        )
        session.add(remediation)
        await session.flush()
        return remediation


# =========================================================================
# AUDIT LOG REPOSITORY
# =========================================================================

class AuditRepository:

    @staticmethod
    async def log(
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        user_email: str,
        action: str,
        entity_target: str,
        entity_id: uuid.UUID,
        client_ip: str,
        user_agent: str,
        before: Optional[dict] = None,
        after: Optional[dict] = None,
    ) -> None:
        entry = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            user_email=user_email,
            action=action,
            entity_target=entity_target,
            entity_id=entity_id,
            client_ip=client_ip,
            user_agent=user_agent,
            state_delta_before=before,
            state_delta_after=after,
        )
        session.add(entry)
        # No flush — audit logs commit with the parent transaction