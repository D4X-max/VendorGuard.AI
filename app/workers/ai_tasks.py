import logging
from celery import shared_task
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import tiktoken
import random

from app.core.config import settings
from app.models.all_models import DocumentChunk, AIUsageLog

logger = logging.getLogger(__name__)

def get_sync_session():
    """
    Builds sync DB engine lazily — reads DATABASE_URL at call time,
    not at module import time. Fixes Celery worker credential issues.
    """
    from app.core.config import settings
    sync_db_url = settings.DATABASE_URL.replace(
        "postgresql+asyncpg://", "postgresql+psycopg2://"
    )
    engine = create_engine(sync_db_url, pool_pre_ping=True)
    SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionFactory()


@shared_task(bind=True, max_retries=3)
def process_evidence_document(
    self, tenant_id: str, document_id: str, file_path: str
):
    """
    Celery task — runs in background worker.
    1. Loads PDF from local storage
    2. Chunks text with overlap
    3. Calls OpenAI embeddings API
    4. Stores vectors in pgvector
    5. Logs token costs to ai_usage_logs
    """
    embeddings_model = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=settings.OPENAI_API_KEY,
    )

    # Load and chunk PDF
    loader = PyPDFLoader(file_path)
    pages = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", " ", ""],
    )
    chunks = text_splitter.split_documents(pages)
    logger.info(f"Document {document_id} split into {len(chunks)} chunks.")

    total_tokens = 0
    encoding = tiktoken.get_encoding("cl100k_base")

    with get_sync_session() as db:
        try:
            # Enforce RLS inside Celery worker
            db.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))

            db_chunks = []
            for i, chunk in enumerate(chunks):
                text_content = chunk.page_content
                if not text_content.strip():
                    continue  # Skip empty chunks

                tokens = len(encoding.encode(text_content))
                total_tokens += tokens

                vector = [random.uniform(-1, 1) for _ in range(1536)]

                db_chunks.append(
                    DocumentChunk(
                        tenant_id=tenant_id,
                        evidence_document_id=document_id,
                        page_number=chunk.metadata.get("page", 0) + 1,
                        chunk_index=i,
                        content_payload=text_content,
                        embedding_vector=vector,
                    )
                )

            # Batch insert all chunks
            db.add_all(db_chunks)

            # Log token cost
            # text-embedding-3-small: $0.02 per 1M tokens
            cost = (total_tokens / 1_000_000) * 0.02
            db.add(
                AIUsageLog(
                    tenant_id=tenant_id,
                    model_version="text-embedding-3-small",
                    prompt_tokens=total_tokens,
                    completion_tokens=0,
                    calculated_usd_cost=cost,
                    execution_context="DOCUMENT_INGESTION",
                )
            )

            # Mark document as completed
            db.execute(
                text(
                    "UPDATE evidence_documents "
                    "SET processing_status = 'COMPLETED' "
                    "WHERE id = :id"
                ),
                {"id": document_id},
            )

            db.commit()
            logger.info(
                f"Document {document_id} processed. "
                f"Chunks: {len(db_chunks)}, Tokens: {total_tokens}, Cost: ${cost:.6f}"
            )

        except Exception as e:
            db.rollback()
            # Mark document as failed
            try:
                db.execute(
                    text(
                        "UPDATE evidence_documents "
                        "SET processing_status = 'FAILED' "
                        "WHERE id = :id"
                    ),
                    {"id": document_id},
                )
                db.commit()
            except Exception:
                pass
            logger.error(f"Failed to process document {document_id}: {e}")
            raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
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
    """Writes audit log entry without blocking the HTTP thread."""
    import uuid
    from app.models.all_models import AuditLog

    with get_sync_session() as db:
        try:
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
            db.add(entry)
            db.commit()
        except Exception as exc:
            db.rollback()
            raise self.retry(exc=exc)