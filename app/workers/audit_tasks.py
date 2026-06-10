import logging
from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="audit.log_event",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def log_audit_event(
    self,
    tenant_id: str,
    user_id: str,
    action: str,
    entity_target: str,
    entity_id: str,
    client_ip: str = "system",
    user_agent: str = "system",
    before: dict = None,
    after: dict = None,
):
    """
    Async Celery task — writes to audit_logs table without
    blocking the main HTTP request thread.
    """
    import asyncio
    from sqlalchemy import text
    from app.core.database import async_session_maker
    from app.models.all_models import AuditLog
    import uuid

    async def _write():
        async with async_session_maker() as session:
            entry = AuditLog(
                tenant_id=uuid.UUID(tenant_id),
                user_id=uuid.UUID(user_id) if user_id else None,
                user_email="system",
                action=action,
                entity_target=entity_target,
                entity_id=uuid.UUID(entity_id),
                client_ip=client_ip,
                user_agent=user_agent,
                state_delta_before=before,
                state_delta_after=after,
            )
            session.add(entry)
            await session.commit()
            logger.info(
                "Audit event logged",
                extra={
                    "action": action,
                    "entity_id": entity_id,
                    "tenant_id": tenant_id,
                },
            )

    try:
        asyncio.run(_write())
    except Exception as exc:
        logger.error(f"Audit log failed: {exc}")
        raise self.retry(exc=exc)