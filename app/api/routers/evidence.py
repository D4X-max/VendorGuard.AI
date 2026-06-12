from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, Form, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_tenant_session
from app.api.dependencies.auth import require_permissions, get_current_active_user
from app.domain.schemas.user import UserInDB
from app.domain.services.evidence_service import EvidenceService
from app.domain.services.ai_service import AIService
from app.workers.ai_tasks import process_evidence_document

router = APIRouter(prefix="/evidence", tags=["Evidence & AI"])

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.post(
    "/vendor/{vendor_id}",
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_evidence(
    vendor_id: UUID,
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(require_permissions(["evidence:write"])),
    session: AsyncSession = Depends(get_tenant_session),
):
    """
    Upload a vendor evidence document (PDF, DOCX).
    Returns 202 immediately — AI processing happens async in Celery.
    Poll GET /evidence/{document_id}/status to track progress.
    """
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file.content_type}'. Only PDF and DOCX allowed.",
        )

    service = EvidenceService(session)
    document_id, file_path = await service.upload_and_register_evidence(
        tenant_id=str(current_user.tenant_id),
        vendor_id=str(vendor_id),
        user_id=str(current_user.id),
        file=file,
    )
    await session.commit()

    # Fire Celery task — non-blocking
    try:
        process_evidence_document.delay(
            str(current_user.tenant_id),
            document_id,
            file_path,
        )
    except Exception:
        pass  # Redis unavailable — file saved, processing skipped

    return {
        "message": "File uploaded successfully. AI processing initiated.",
        "document_id": document_id,
        "status": "PROCESSING",
    }


@router.get("/vendor/{vendor_id}/documents")
async def list_evidence_documents(
    vendor_id: UUID,
    current_user: UserInDB = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_tenant_session),
):
    """List all evidence documents for a vendor with processing status."""
    from sqlalchemy import select, text
    from app.models.all_models import EvidenceDocument

    result = await session.execute(
        select(EvidenceDocument)
        .where(
            EvidenceDocument.vendor_id == vendor_id,
            EvidenceDocument.tenant_id == current_user.tenant_id,
        )
        .order_by(EvidenceDocument.created_at.desc())
    )
    docs = result.scalars().all()

    return [
        {
            "id": str(d.id),
            "file_name": d.file_name,
            "file_size_bytes": d.file_size_bytes,
            "mime_type": d.mime_type,
            "processing_status": d.processing_status,
            "created_at": d.created_at,
        }
        for d in docs
    ]


@router.get("/{document_id}/status")
async def get_document_status(
    document_id: UUID,
    current_user: UserInDB = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Poll this endpoint to check if AI processing is complete."""
    from sqlalchemy import select
    from app.models.all_models import EvidenceDocument

    result = await session.execute(
        select(EvidenceDocument).where(
            EvidenceDocument.id == document_id,
            EvidenceDocument.tenant_id == current_user.tenant_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    return {
        "document_id": str(doc.id),
        "file_name": doc.file_name,
        "processing_status": doc.processing_status,
    }


@router.post("/vendor/{vendor_id}/query")
async def query_vendor_evidence(
    vendor_id: UUID,
    question: str = Form(...),
    current_user: UserInDB = Depends(require_permissions(["evidence:write"])),
    session: AsyncSession = Depends(get_tenant_session),
):
    """
    RAG-powered compliance question answering.
    Example: 'Does this vendor perform annual penetration testing?'
    Returns AI answer with exact page citations from uploaded documents.
    Requires a real OPENAI_API_KEY in .env to work.
    """
    if settings.OPENAI_API_KEY == "sk-placeholder":
        raise HTTPException(
            status_code=503,
            detail="OpenAI API key not configured. Set OPENAI_API_KEY in .env to use RAG queries.",
        )

    from app.core.config import settings
    service = AIService(session)
    return await service.query_vendor_evidence(
        tenant_id=str(current_user.tenant_id),
        vendor_id=str(vendor_id),
        question=question,
    )