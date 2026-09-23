from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from app.core.config import settings


class WhitelistMiddleware(BaseMiddleware):
    """Silently drops updates from telegram_id not in ALLOWED_TELEGRAM_IDS."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if user is None or user.id not in settings.allowed_telegram_id_set:
            return None
        return await handler(event, data)
