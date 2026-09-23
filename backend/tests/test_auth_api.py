import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest
from httpx import AsyncClient

from app.auth.jwt import create_access_token, decode_access_token
from app.auth.telegram_verify import InitDataError, verify_init_data
from app.core.config import settings as app_settings

BOT_TOKEN = "123456:test-bot-token"


def _build_init_data(*, telegram_id: int, first_name: str = "Тест", auth_date: int | None = None) -> str:
    payload = {
        "user": json.dumps({"id": telegram_id, "first_name": first_name}, ensure_ascii=False),
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "query_id": "AAABBBCCC",
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(payload.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    payload["hash"] = computed_hash
    return urlencode(payload)


def test_verify_init_data_accepts_valid_signature() -> None:
    init_data = _build_init_data(telegram_id=111)
    pairs = verify_init_data(init_data, BOT_TOKEN)
    assert json.loads(pairs["user"])["id"] == 111


def test_verify_init_data_rejects_tampered_hash() -> None:
    init_data = _build_init_data(telegram_id=111) + "x"
    with pytest.raises(InitDataError):
        verify_init_data(init_data, BOT_TOKEN)


def test_verify_init_data_rejects_stale_auth_date() -> None:
    init_data = _build_init_data(telegram_id=111, auth_date=int(time.time()) - 100_000)
    with pytest.raises(InitDataError):
        verify_init_data(init_data, BOT_TOKEN)


def test_jwt_roundtrip() -> None:
    token = create_access_token(user_id=7, telegram_id=111)
    payload = decode_access_token(token)
    assert payload["sub"] == "7"
    assert payload["telegram_id"] == 111


async def test_auth_telegram_endpoint_issues_token_for_whitelisted_user(
    api_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(app_settings, "telegram_bot_token", BOT_TOKEN)
    monkeypatch.setattr(app_settings, "allowed_telegram_ids", "111")

    init_data = _build_init_data(telegram_id=111, first_name="Мама")
    response = await api_client.post("/api/v1/auth/telegram", json={"init_data": init_data})

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["name"] == "Мама"


async def test_auth_telegram_endpoint_rejects_unwhitelisted_user(
    api_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(app_settings, "telegram_bot_token", BOT_TOKEN)
    monkeypatch.setattr(app_settings, "allowed_telegram_ids", "111")

    init_data = _build_init_data(telegram_id=999)
    response = await api_client.post("/api/v1/auth/telegram", json={"init_data": init_data})

    assert response.status_code == 403


async def test_protected_endpoint_requires_token(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/patient")
    assert response.status_code == 401
