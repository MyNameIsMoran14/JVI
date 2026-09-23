from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.documents.models import Document, DocumentStatus
from app.extraction.models import LabResult


async def confirm_document(session: AsyncSession, document_id: int) -> int:
    """Marks all pending lab_results for a document as confirmed. Returns rows affected."""
    result = await session.execute(
        update(LabResult).where(LabResult.document_id == document_id).values(confirmed=True)
    )
    document = await session.get(Document, document_id)
    if document is not None:
        document.status = DocumentStatus.confirmed
    await session.commit()
    return result.rowcount or 0


async def discard_document(session: AsyncSession, document_id: int) -> None:
    """Drops unconfirmed lab_results for a document (user said the recognition was wrong)."""
    await session.execute(delete(LabResult).where(LabResult.document_id == document_id))
    document = await session.get(Document, document_id)
    if document is not None:
        document.status = DocumentStatus.failed
    await session.commit()
