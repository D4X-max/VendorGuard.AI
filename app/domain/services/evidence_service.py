import os
import uuid
import hashlib
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.all_models import EvidenceDocument


class EvidenceService:
    def __init__(self, session: AsyncSession):
        self.session = session
        os.makedirs(settings.LOCAL_STORAGE_DIR, exist_ok=True)

    async def upload_and_register_evidence(
        self,
        tenant_id: str,
        vendor_id: str,
        user_id: str,
        file: UploadFile,
    ) -> tuple[str, str]:
        """
        Saves file to local storage, calculates SHA256,
        creates EvidenceDocument DB record.
        Returns (document_id, absolute_file_path).
        """
        file_ext = file.filename.split(".")[-1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        relative_path = f"tenants/{tenant_id}/vendors/{vendor_id}/{unique_filename}"
        absolute_path = os.path.join(settings.LOCAL_STORAGE_DIR, relative_path)

        # Create directories if they don't exist
        os.makedirs(os.path.dirname(absolute_path), exist_ok=True)

        # Read file content once
        file_content = await file.read()

        # Calculate SHA256 checksum
        sha256_hash = hashlib.sha256(file_content).hexdigest()

        # Write to disk
        with open(absolute_path, "wb") as f:
            f.write(file_content)

        # Register in DB
        new_doc = EvidenceDocument(
            tenant_id=tenant_id,
            vendor_id=vendor_id,
            file_name=file.filename,
            s3_storage_key=absolute_path,
            file_size_bytes=len(file_content),
            mime_type=file.content_type or "application/octet-stream",
            uploaded_by=user_id,
            sha256_checksum=sha256_hash,
            processing_status="PENDING",
        )
        self.session.add(new_doc)
        await self.session.flush()

        return str(new_doc.id), absolute_path