from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.context import build_context, compute_key_trends
from app.auth.models import User, UserRole
from app.documents.models import Document, DocumentKind, DocumentStatus
from app.extraction.models import Analyte, LabResult
from app.patient.models import Patient


async def _make_patient(session: AsyncSession, **kwargs) -> Patient:
    patient = Patient(full_name="Тараев Виталий Викторович", **kwargs)
    session.add(patient)
    await session.commit()
    await session.refresh(patient)
    return patient


async def _make_document(session: AsyncSession, patient_id: int, sha256: str) -> Document:
    user = User(telegram_id=hash(sha256) % 1_000_000, name="Тест", role=UserRole.editor)
    session.add(user)
    await session.commit()
    await session.refresh(user)

    document = Document(
        patient_id=patient_id,
        kind=DocumentKind.lab,
        file_path="x",
        mime="image/jpeg",
        sha256=sha256,
        status=DocumentStatus.confirmed,
        uploaded_by=user.id,
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    return document


async def test_compute_key_trends_shows_change_percent(session: AsyncSession) -> None:
    patient = await _make_patient(session)
    doc1 = await _make_document(session, patient.id, "a" * 64)
    doc2 = await _make_document(session, patient.id, "b" * 64)

    flc = Analyte(
        code="FLC_RATIO", name_ru="Соотношение κ/λ", canonical_unit="", aliases=[], group="tumor", is_key=True
    )
    session.add(flc)
    await session.commit()

    session.add_all(
        [
            LabResult(
                document_id=doc1.id,
                analyte_id=flc.id,
                taken_at=date(2026, 1, 1),
                value=12.4,
                raw_name="κ/λ",
                confirmed=True,
            ),
            LabResult(
                document_id=doc2.id,
                analyte_id=flc.id,
                taken_at=date(2026, 3, 1),
                value=8.1,
                raw_name="κ/λ",
                confirmed=True,
            ),
        ]
    )
    await session.commit()

    lines = await compute_key_trends(session, patient.id)
    assert len(lines) == 1
    assert "Соотношение κ/λ" in lines[0]
    assert "-35%" in lines[0] or "−35%" in lines[0]


async def test_compute_key_trends_ignores_unconfirmed(session: AsyncSession) -> None:
    patient = await _make_patient(session)
    document = await _make_document(session, patient.id, "c" * 64)

    hgb = Analyte(code="HGB", name_ru="Гемоглобин", canonical_unit="г/л", aliases=[], group="blood", is_key=True)
    session.add(hgb)
    await session.commit()

    session.add(
        LabResult(
            document_id=document.id,
            analyte_id=hgb.id,
            taken_at=date(2026, 1, 1),
            value=140,
            raw_name="HGB",
            confirmed=False,
        )
    )
    await session.commit()

    assert await compute_key_trends(session, patient.id) == []


async def test_build_context_includes_diagnosis_and_never_leaks_full_name(session: AsyncSession) -> None:
    patient = await _make_patient(
        session, birth_year=1968, diagnosis="C90.0 Множественная миелома", stage="ISS III"
    )

    context = await build_context(session, patient.id)

    assert "Множественная миелома" in context
    assert "ISS III" in context
    assert "лет" in context
    assert "Тараев" not in context
    assert "Викторович" not in context


async def test_build_context_handles_bare_patient(session: AsyncSession) -> None:
    patient = await _make_patient(session)
    context = await build_context(session, patient.id)
    assert "Пациент" in context
