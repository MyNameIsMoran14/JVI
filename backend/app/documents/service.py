import hashlib
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.documents.models import Document, DocumentKind, DocumentStatus


def _resolve_extension(filename: str, mime: str) -> str:
    suffix = Path(filename).suffix
    if suffix:
        return suffix
    return {
        "application/pdf": ".pdf",
        "image/jpeg": ".jpg",
        "image/png": ".png",
    }.get(mime, "")


async def find_by_sha256(session: AsyncSession, sha256: str) -> Document | None:
    result = await session.execute(select(Document).where(Document.sha256 == sha256))
    return result.scalar_one_or_none()


async def save_document(
    session: AsyncSession,
    *,
    patient_id: int,
    uploaded_by: int,
    kind: DocumentKind,
    filename: str,
    mime: str,
    content: bytes,
    taken_at: date | None = None,
    lab_name: str | None = None,
) -> tuple[Document, bool]:
    """Store an uploaded file and create its `documents` row.

    Returns `(document, created)` — `created` is `False` when a document with
    the same sha256 already exists, per the spec's dedup rule (section 6, step 1).
    """
    sha256 = hashlib.sha256(content).hexdigest()

    existing = await find_by_sha256(session, sha256)
    if existing is not None:
        return existing, False

    extension = _resolve_extension(filename, mime)
    relative_dir = Path(sha256[:2]) / sha256[2:4]
    target_dir = Path(settings.files_dir) / relative_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{sha256}{extension}"
    target_path.write_bytes(content)

    document = Document(
        patient_id=patient_id,
        kind=kind,
        file_path=str(relative_dir / f"{sha256}{extension}"),
        mime=mime,
        sha256=sha256,
        taken_at=taken_at,
        lab_name=lab_name,
        status=DocumentStatus.uploaded,
        uploaded_by=uploaded_by,
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    return document, True
