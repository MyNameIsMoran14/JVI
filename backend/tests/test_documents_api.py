from datetime import date
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User, UserRole
from app.core.config import settings as app_settings
from app.documents.models import Document, DocumentKind, DocumentStatus
from app.extraction.models import Analyte, LabResult
from app.patient.models import Patient


@pytest.fixture
def files_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(app_settings, "files_dir", str(tmp_path))
    return tmp_path


async def _seed_document(session: AsyncSession, files_dir: Path) -> tuple[Patient, Document]:
    patient = Patient(full_name="Пациент")
    user = User(telegram_id=333, name="Загрузчик", role=UserRole.editor)
    session.add_all([patient, user])
    await session.commit()
    await session.refresh(patient)
    await session.refresh(user)

    file_path = "aa/test.jpg"
    full_path = files_dir / file_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(b"fake-image-bytes")

    document = Document(
        patient_id=patient.id,
        kind=DocumentKind.lab,
        file_path=file_path,
        mime="image/jpeg",
        sha256="a" * 64,
        status=DocumentStatus.needs_review,
        uploaded_by=user.id,
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)

    hgb = Analyte(code="HGB", name_ru="Гемоглобин", canonical_unit="г/л", aliases=[], group="blood", is_key=True)
    session.add(hgb)
    await session.commit()
    await session.refresh(hgb)

    session.add(
        LabResult(
            document_id=document.id,
            analyte_id=hgb.id,
            taken_at=date(2026, 1, 1),
            value=118,
            unit="г/л",
            raw_name="HGB",
            confirmed=False,
        )
    )
    await session.commit()
    return patient, document


async def test_list_documents(
    api_client: AsyncClient, session: AsyncSession, files_dir: Path, authed_headers: dict[str, str]
) -> None:
    await _seed_document(session, files_dir)

    response = await api_client.get("/api/v1/documents", headers=authed_headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["status"] == "needs_review"


async def test_get_document_file(
    api_client: AsyncClient, session: AsyncSession, files_dir: Path, authed_headers: dict[str, str]
) -> None:
    _patient, document = await _seed_document(session, files_dir)

    response = await api_client.get(f"/api/v1/documents/{document.id}/file", headers=authed_headers)

    assert response.status_code == 200
    assert response.content == b"fake-image-bytes"


async def test_get_document_extraction(
    api_client: AsyncClient, session: AsyncSession, files_dir: Path, authed_headers: dict[str, str]
) -> None:
    _patient, document = await _seed_document(session, files_dir)

    response = await api_client.get(f"/api/v1/documents/{document.id}/extraction", headers=authed_headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["analyte_code"] == "HGB"
    assert body[0]["confirmed"] is False


async def test_confirm_document(
    api_client: AsyncClient,
    session: AsyncSession,
    files_dir: Path,
    authed_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.documents import router as documents_router_module

    async def fake_rebuild_summary(_session, _patient_id) -> None:  # noqa: ANN001
        return None

    monkeypatch.setattr(documents_router_module, "rebuild_patient_summary", fake_rebuild_summary)

    _patient, document = await _seed_document(session, files_dir)

    response = await api_client.post(f"/api/v1/documents/{document.id}/confirm", headers=authed_headers)

    assert response.status_code == 200
    assert response.json()["confirmed"] == 1


async def test_document_not_belonging_to_patient_is_404(
    api_client: AsyncClient, authed_headers: dict[str, str]
) -> None:
    response = await api_client.get("/api/v1/documents/999/file", headers=authed_headers)
    assert response.status_code == 404
