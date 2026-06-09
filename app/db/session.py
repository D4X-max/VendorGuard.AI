from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from app.config import settings


# ─────────────────────────────────────────────
# Async Engine
# ─────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,          # Detects stale connections before use
    pool_recycle=3600,           # Recycle connections every hour
    echo=settings.is_development, # Log SQL only in dev
)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ─────────────────────────────────────────────
# Declarative Base for all ORM models
# ─────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ─────────────────────────────────────────────
# Multi-Tenant Session with RLS Context Injection
# ─────────────────────────────────────────────
async def get_tenant_session(tenant_id: str):
    """
    Yields an async DB session with RLS tenant context injected.

    Flow:
      1. Open a new session from the pool
      2. SET LOCAL app.current_tenant_id → scoped to this transaction only
      3. Yield session to the repository layer
      4. On exit: RESET context → return connection cleanly to pool

    This prevents tenant context from bleeding between requests.
    """
    async with AsyncSessionFactory() as session:
        try:
            await session.execute(
                text("SET LOCAL app.current_tenant_id = :tid"),
                {"tid": str(tenant_id)},
            )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            # CRITICAL: Always reset tenant context before pool reuse
            try:
                await session.execute(text("RESET app.current_tenant_id"))
            except Exception:
                pass  # Session may already be closed


# ─────────────────────────────────────────────
# Raw Session (for superuser/system operations only)
# e.g., tenant provisioning, migrations
# ─────────────────────────────────────────────
async def get_system_session():
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise