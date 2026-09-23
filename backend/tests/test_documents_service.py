from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User, UserRole
from app.core.config import settings as app_settings
from app.documents.models import DocumentKind
from app.documents.service import save_document
from app.patient.models import Patient


@pytest.fixture
def files_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(app_settings, "files_dir", str(tmp_path))
    return tmp_path


async def _make_patient_and_user(session: AsyncSession, telegram_id: int) -> tuple[Patient, User]:
    patient = Patient(full_name="Тестовый пациент")
    user = User(telegram_id=telegram_id, name="Мама", role=UserRole.editor)
    session.add_all([patient, user])
    await session.commit()
    await session.refresh(patient)
    await session.refresh(user)
    return patient, user


async def test_save_document_creates_row_and_file(session: AsyncSession, files_dir: Path) -> None:
    patient, user = await _make_patient_and_user(session, telegram_id=1)

    document, created = await save_document(
        session,
        patient_id=patient.id,
        uploaded_by=user.id,
        kind=DocumentKind.lab,
        filename="analysis.pdf",
        mime="application/pdf",
        content=b"%PDF-1.4 fake content",
    )

    assert created is True
    assert document.id is not None
    stored_path = files_dir / document.file_path
    assert stored_path.exists()
    assert stored_path.read_bytes() == b"%PDF-1.4 fake content"


async def test_save_document_dedupes_by_sha256(session: AsyncSession, files_dir: Path) -> None:
    patient, user = await _make_patient_and_user(session, telegram_id=2)

    kwargs = dict(
        patient_id=patient.id,
        uploaded_by=user.id,
        kind=DocumentKind.lab,
        filename="analysis.pdf",
        mime="application/pdf",
        content=b"same bytes",
    )

    first, first_created = await save_document(session, **kwargs)
    second, second_created = await save_document(session, **kwargs)

    assert first_created is True
    assert second_created is False
    assert first.id == second.id
