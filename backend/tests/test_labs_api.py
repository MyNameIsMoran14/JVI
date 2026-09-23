from datetime import date

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User, UserRole
from app.documents.models import Document, DocumentKind, DocumentStatus
from app.extraction.models import Analyte, LabResult
from app.patient.models import Patient


async def _seed_lab_history(session: AsyncSession) -> Patient:
    patient = Patient(full_name="Пациент")
    user = User(telegram_id=222, name="Загрузчик", role=UserRole.editor)
    session.add_all([patient, user])
    await session.commit()
    await session.refresh(patient)
    await session.refresh(user)

    hgb = Analyte(code="HGB", name_ru="Гемоглобин", canonical_unit="г/л", aliases=[], group="blood", is_key=True)
    session.add(hgb)
    await session.commit()
    await session.refresh(hgb)

    for i, (taken_at, value) in enumerate([(date(2026, 1, 1), 140.0), (date(2026, 2, 1), 120.0)]):
        document = Document(
            patient_id=patient.id,
            kind=DocumentKind.lab,
            file_path="x",
            mime="image/jpeg",
            sha256=f"{i}" * 64,
            status=DocumentStatus.confirmed,
            uploaded_by=user.id,
        )
        session.add(document)
        await session.commit()
        await session.refresh(document)
        session.add(
            LabResult(
                document_id=document.id,
                analyte_id=hgb.id,
                taken_at=taken_at,
                value=value,
                value_canonical=value,
                unit="г/л",
                raw_name="HGB",
                confirmed=True,
            )
        )
    await session.commit()
    return patient


async def test_labs_latest_returns_key_analytes_with_change(
    api_client: AsyncClient, session: AsyncSession, authed_headers: dict[str, str]
) -> None:
    await _seed_lab_history(session)

    response = await api_client.get("/api/v1/labs/latest", headers=authed_headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["code"] == "HGB"
    assert body[0]["value"] == 120.0
    assert body[0]["previous_value"] == 140.0
    assert round(body[0]["change_pct"]) == round((120.0 - 140.0) / 140.0 * 100)


async def test_labs_series_returns_points_in_chronological_order(
    api_client: AsyncClient, session: AsyncSession, authed_headers: dict[str, str]
) -> None:
    await _seed_lab_history(session)

    response = await api_client.get("/api/v1/labs/series", params={"codes": "HGB"}, headers=authed_headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    points = body[0]["points"]
    assert [p["value"] for p in points] == [140.0, 120.0]
