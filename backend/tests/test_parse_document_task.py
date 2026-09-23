from collections.abc import Callable
from datetime import date
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User, UserRole
from app.core.config import settings as app_settings
from app.documents.models import Document, DocumentKind, DocumentStatus
from app.extraction import tasks as tasks_module
from app.extraction.models import Analyte, LabResult
from app.extraction.schemas import LabItem, LabReport
from app.patient.models import Patient


@pytest.fixture
def files_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(app_settings, "files_dir", str(tmp_path))
    return tmp_path


async def _make_fixture_document(
    session: AsyncSession, files_dir: Path, *, mime: str = "image/jpeg"
) -> tuple[Document, Patient, User]:
    patient = Patient(full_name="Тестовый пациент")
    user = User(telegram_id=42, name="Тест", role=UserRole.editor)
    session.add_all([patient, user])
    await session.commit()
    await session.refresh(patient)
    await session.refresh(user)

    image = Image.new("RGB", (100, 300), color="white")
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    file_path = "aa/bb/test.jpg"
    full_path = files_dir / file_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(buffer.getvalue())

    document = Document(
        patient_id=patient.id,
        kind=DocumentKind.lab,
        file_path=file_path,
        mime=mime,
        sha256="a" * 64,
        status=DocumentStatus.uploaded,
        uploaded_by=user.id,
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    return document, patient, user


async def test_parse_document_saves_matched_results_and_notifies(
    session: AsyncSession,
    files_dir: Path,
    db_session_maker: Callable[[], AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document, patient, user = await _make_fixture_document(session, files_dir)

    hgb = Analyte(
        code="HGB", name_ru="Гемоглобин", canonical_unit="г/л", aliases=["HGB", "Hb"], group="blood", is_key=True
    )
    session.add(hgb)
    await session.commit()

    async def fake_extract(*, text: str | None = None, images_b64: list[str] | None = None) -> LabReport:
        return LabReport(
            taken_at=date(2026, 1, 15),
            lab_name="Тестовая лаборатория",
            items=[
                LabItem(raw_name="HGB", value=118, unit="г/л", ref_low=130, ref_high=160),
                LabItem(raw_name="Совсем неизвестный показатель", value=1, unit="ед"),
            ],
        )

    notifications: list[tuple] = []

    async def fake_notify(uploader, text, markup=None) -> None:  # noqa: ANN001
        notifications.append((uploader, text, markup))

    monkeypatch.setattr(tasks_module, "extract_lab_report", fake_extract)
    monkeypatch.setattr(tasks_module, "_notify", fake_notify)
    monkeypatch.setattr(tasks_module, "async_session_maker", db_session_maker)

    await tasks_module.parse_document({}, document.id)

    async with db_session_maker() as verify_session:
        refreshed = await verify_session.get(Document, document.id)
        assert refreshed is not None
        assert refreshed.status == DocumentStatus.needs_review

        from sqlalchemy import select

        results = list((await verify_session.execute(select(LabResult))).scalars())
        assert len(results) == 1
        result = results[0]
        assert result.analyte_id == hgb.id
        assert result.value == 118
        assert result.value_canonical == 118
        assert result.flag.value == "L"
        assert result.confirmed is False

    assert len(notifications) == 1
    _, text, markup = notifications[0]
    assert "Гемоглобин" in text
    assert "Не распознал" in text
    assert "Совсем неизвестный показатель" in text
    assert markup is not None


async def test_parse_document_marks_failed_on_extraction_error(
    session: AsyncSession,
    files_dir: Path,
    db_session_maker: Callable[[], AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document, _patient, _user = await _make_fixture_document(session, files_dir)

    async def failing_extract(*, text: str | None = None, images_b64: list[str] | None = None) -> LabReport:
        raise RuntimeError("boom")

    notifications: list[tuple] = []

    async def fake_notify(uploader, text, markup=None) -> None:  # noqa: ANN001
        notifications.append((uploader, text, markup))

    monkeypatch.setattr(tasks_module, "extract_lab_report", failing_extract)
    monkeypatch.setattr(tasks_module, "_notify", fake_notify)
    monkeypatch.setattr(tasks_module, "async_session_maker", db_session_maker)

    await tasks_module.parse_document({}, document.id)

    async with db_session_maker() as verify_session:
        refreshed = await verify_session.get(Document, document.id)
        assert refreshed is not None
        assert refreshed.status == DocumentStatus.failed

    assert len(notifications) == 1
    assert "не получилось" in notifications[0][1].lower()
