from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.summary import rebuild_patient_summary
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.config import settings
from app.core.db import get_session
from app.documents.models import Document
from app.documents.schemas import DocumentRead, LabResultRead
from app.extraction.models import Analyte, LabResult
from app.extraction.service import confirm_document, discard_document
from app.patient.service import get_or_create_default_patient

router = APIRouter(prefix="/documents", tags=["documents"])


async def _get_own_document(session: AsyncSession, document_id: int) -> Document:
    patient = await get_or_create_default_patient(session)
    document = await session.get(Document, document_id)
    if document is None or document.patient_id != patient.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return document


@router.get("", response_model=list[DocumentRead])
async def list_documents(
    kind: str | None = None,
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> list[DocumentRead]:
    patient = await get_or_create_default_patient(session)
    stmt = select(Document).where(Document.patient_id == patient.id).order_by(Document.created_at.desc())
    if kind:
        stmt = stmt.where(Document.kind == kind)
    if date_from:
        stmt = stmt.where(Document.taken_at >= date_from)
    if date_to:
        stmt = stmt.where(Document.taken_at <= date_to)

    documents = list((await session.execute(stmt)).scalars())
    return [DocumentRead.model_validate(d) for d in documents]


@router.get("/{document_id}/file")
async def get_document_file(
    document_id: int,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> FileResponse:
    document = await _get_own_document(session, document_id)
    path = Path(settings.files_dir) / document.file_path
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File missing on disk")
    return FileResponse(path, media_type=document.mime)


@router.get("/{document_id}/extraction", response_model=list[LabResultRead])
async def get_document_extraction(
    document_id: int,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> list[LabResultRead]:
    await _get_own_document(session, document_id)
    stmt = select(LabResult, Analyte).join(Analyte, Analyte.id == LabResult.analyte_id).where(
        LabResult.document_id == document_id
    )
    rows = (await session.execute(stmt)).all()
    return [
        LabResultRead(
            id=lr.id,
            analyte_code=a.code,
            analyte_name=a.name_ru,
            value=lr.value,
            value_text=lr.value_text,
            unit=lr.unit,
            ref_low=lr.ref_low,
            ref_high=lr.ref_high,
            flag=lr.flag.value if lr.flag else None,
            confirmed=lr.confirmed,
        )
        for lr, a in rows
    ]


@router.post("/{document_id}/confirm")
async def confirm_document_endpoint(
    document_id: int,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> dict[str, int]:
    document = await _get_own_document(session, document_id)
    count = await confirm_document(session, document_id)
    await rebuild_patient_summary(session, document.patient_id)
    return {"confirmed": count}


@router.post("/{document_id}/discard")
async def discard_document_endpoint(
    document_id: int,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> dict[str, str]:
    await _get_own_document(session, document_id)
    await discard_document(session, document_id)
    return {"status": "discarded"}
