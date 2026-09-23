from typing import Any

import pytest
from aiogram.types import User

from app.bot.middlewares import WhitelistMiddleware
from app.core.config import settings as app_settings


@pytest.fixture(autouse=True)
def whitelist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_settings, "allowed_telegram_ids", "111")


async def test_whitelist_allows_listed_user() -> None:
    middleware = WhitelistMiddleware()
    called = False

    async def handler(event: Any, data: dict[str, Any]) -> str:
        nonlocal called
        called = True
        return "ok"

    user = User(id=111, is_bot=False, first_name="Мама")
    result = await middleware(handler, event=object(), data={"event_from_user": user})

    assert result == "ok"
    assert called is True


async def test_whitelist_blocks_unlisted_user() -> None:
    middleware = WhitelistMiddleware()

    async def handler(event: Any, data: dict[str, Any]) -> str:
        raise AssertionError("handler must not run for a telegram_id outside the whitelist")

    user = User(id=999, is_bot=False, first_name="Чужой")
    result = await middleware(handler, event=object(), data={"event_from_user": user})

    assert result is None


async def test_whitelist_blocks_missing_user() -> None:
    middleware = WhitelistMiddleware()

    async def handler(event: Any, data: dict[str, Any]) -> str:
        raise AssertionError("handler must not run without event_from_user")

    result = await middleware(handler, event=object(), data={})

    assert result is None
