from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.red_flags import check_lab_red_flags, check_text_red_flags, format_red_flag_notice
from app.documents.models import Document, DocumentKind, DocumentStatus
from app.extraction.models import Analyte, LabResult, ResultFlag
from app.patient.models import Patient


async def _make_patient(session: AsyncSession) -> Patient:
    patient = Patient(full_name="Тестовый пациент")
    session.add(patient)
    await session.commit()
    await session.refresh(patient)
    return patient


async def _make_document(session: AsyncSession, patient_id: int, sha256: str) -> Document:
    from app.auth.models import User, UserRole

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


async def test_check_lab_red_flags_out_of_range(session: AsyncSession) -> None:
    patient = await _make_patient(session)
    document = await _make_document(session, patient.id, "a" * 64)

    creatinine = Analyte(
        code="CREATININE", name_ru="Креатинин", canonical_unit="мкмоль/л", aliases=[], group="kidneys", is_key=True
    )
    session.add(creatinine)
    await session.commit()

    session.add(
        LabResult(
            document_id=document.id,
            analyte_id=creatinine.id,
            taken_at=date(2026, 1, 1),
            value=250,
            unit="мкмоль/л",
            ref_low=60,
            ref_high=110,
            flag=ResultFlag.high,
            raw_name="Креатинин",
            confirmed=True,
        )
    )
    await session.commit()

    flags = await check_lab_red_flags(session, patient.id)
    assert any("Креатинин" in f and "выше" in f for f in flags)


async def test_check_lab_red_flags_sharp_drop(session: AsyncSession) -> None:
    patient = await _make_patient(session)
    doc1 = await _make_document(session, patient.id, "b" * 64)
    doc2 = await _make_document(session, patient.id, "c" * 64)

    hgb = Analyte(code="HGB", name_ru="Гемоглобин", canonical_unit="г/л", aliases=[], group="blood", is_key=True)
    session.add(hgb)
    await session.commit()

    session.add_all(
        [
            LabResult(
                document_id=doc1.id,
                analyte_id=hgb.id,
                taken_at=date(2026, 1, 1),
                value=140,
                unit="г/л",
                raw_name="HGB",
                confirmed=True,
            ),
            LabResult(
                document_id=doc2.id,
                analyte_id=hgb.id,
                taken_at=date(2026, 2, 1),
                value=95,  # ~32% drop, above the 20% threshold
                unit="г/л",
                raw_name="HGB",
                confirmed=True,
            ),
        ]
    )
    await session.commit()

    flags = await check_lab_red_flags(session, patient.id)
    assert any("Гемоглобин" in f and "резко снизился" in f for f in flags)


async def test_check_lab_red_flags_stable_values_no_flag(session: AsyncSession) -> None:
    patient = await _make_patient(session)
    doc1 = await _make_document(session, patient.id, "d" * 64)
    doc2 = await _make_document(session, patient.id, "e" * 64)

    hgb = Analyte(code="HGB", name_ru="Гемоглобин", canonical_unit="г/л", aliases=[], group="blood", is_key=True)
    session.add(hgb)
    await session.commit()

    session.add_all(
        [
            LabResult(
                document_id=doc1.id,
                analyte_id=hgb.id,
                taken_at=date(2026, 1, 1),
                value=140,
                unit="г/л",
                raw_name="HGB",
                confirmed=True,
            ),
            LabResult(
                document_id=doc2.id,
                analyte_id=hgb.id,
                taken_at=date(2026, 2, 1),
                value=138,
                unit="г/л",
                raw_name="HGB",
                confirmed=True,
            ),
        ]
    )
    await session.commit()

    flags = await check_lab_red_flags(session, patient.id)
    assert flags == []


def test_check_text_red_flags_matches_keyword() -> None:
    flags = check_text_red_flags("у него поднялась температура после химии, что делать?")
    assert "температура на фоне химиотерапии" in flags


def test_check_text_red_flags_no_match() -> None:
    assert check_text_red_flags("как расшифровать этот анализ?") == []


def test_format_red_flag_notice_lists_all_flags() -> None:
    text = format_red_flag_notice(["флаг раз", "флаг два"])
    assert "флаг раз" in text
    assert "флаг два" in text
    assert "врач" in text.lower()
