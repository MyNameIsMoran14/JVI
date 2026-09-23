from collections.abc import Callable

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token
from app.auth.models import User, UserRole
from app.core.config import settings as app_settings


async def _auth_headers(
    db_session_maker: Callable[[], AsyncSession], monkeypatch: pytest.MonkeyPatch, telegram_id: int = 111
) -> dict[str, str]:
    async with db_session_maker() as session:
        user = User(telegram_id=telegram_id, name="Тест", role=UserRole.editor)
        session.add(user)
        await session.commit()
        await session.refresh(user)

    monkeypatch.setattr(app_settings, "allowed_telegram_ids", str(telegram_id))
    token = create_access_token(user_id=user.id, telegram_id=telegram_id)
    return {"Authorization": f"Bearer {token}"}


async def test_read_patient_creates_default(
    api_client: AsyncClient, db_session_maker: Callable[[], AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _auth_headers(db_session_maker, monkeypatch)
    response = await api_client.get("/api/v1/patient", headers=headers)

    assert response.status_code == 200
    assert response.json()["full_name"] == "Пациент"


async def test_patch_patient_updates_fields(
    api_client: AsyncClient, db_session_maker: Callable[[], AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _auth_headers(db_session_maker, monkeypatch)

    response = await api_client.patch(
        "/api/v1/patient",
        headers=headers,
        json={"diagnosis": "C90.0 Множественная миелома", "stage": "ISS III", "birth_year": 1968},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["diagnosis"] == "C90.0 Множественная миелома"
    assert body["stage"] == "ISS III"
    assert body["birth_year"] == 1968
