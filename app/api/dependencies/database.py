from typing import AsyncGenerator
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import async_session_maker
from app.api.dependencies.auth import get_current_user
from app.domain.schemas.user import UserInDB


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Raw session for system-level operations like tenant registration.
    No RLS context injected.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_tenant_session(
    current_user: UserInDB = Depends(get_current_user),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Tenant-scoped session — opens its OWN session independently.
    Does NOT depend on get_db_session to avoid double-commit conflicts.
    Injects RLS tenant context before yielding.
    """
    async with async_session_maker() as session:
        try:
            await session.execute(
                text(f"SET LOCAL app.current_tenant_id = '{current_user.tenant_id}'")
            )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            try:
                await session.execute(text("RESET app.current_tenant_id"))
            except Exception:
                pass