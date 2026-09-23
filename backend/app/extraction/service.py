from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.documents.models import Document, DocumentStatus
from app.extraction.models import Analyte, LabResult
from app.extraction.normalize import slugify_code


async def get_or_create_unmatched_analyte(
    session: AsyncSession, raw_name: str, unit: str | None
) -> Analyte:
    """Registers a not-yet-known analyte instead of dropping it — nothing gets lost.

    The code is deterministic from raw_name, so the same unrecognized label reuses the
    same analyte on later uploads instead of spawning duplicates. `canonical_unit` is
    just whatever unit the form printed — there's no reference conversion table for it yet.
    """
    code = slugify_code(raw_name)
    existing = await session.execute(select(Analyte).where(Analyte.code == code))
    analyte = existing.scalar_one_or_none()
    if analyte is not None:
        return analyte

    analyte = Analyte(
        code=code,
        name_ru=raw_name,
        canonical_unit=unit,
        aliases=[raw_name],
        group="auto",
        is_key=False,
    )
    session.add(analyte)
    await session.flush()
    return analyte


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
