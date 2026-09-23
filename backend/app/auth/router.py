import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token
from app.auth.service import get_or_create_user
from app.auth.telegram_verify import InitDataError, verify_init_data
from app.core.config import settings
from app.core.db import get_session

router = APIRouter(prefix="/auth", tags=["auth"])


class TelegramAuthRequest(BaseModel):
    init_data: str


class TelegramAuthResponse(BaseModel):
    access_token: str
    name: str


@router.post("/telegram", response_model=TelegramAuthResponse)
async def auth_telegram(
    body: TelegramAuthRequest, session: AsyncSession = Depends(get_session)
) -> TelegramAuthResponse:
    if not settings.telegram_bot_token:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Bot token not configured")

    try:
        pairs = verify_init_data(body.init_data, settings.telegram_bot_token)
    except InitDataError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    user_json = pairs.get("user")
    if not user_json:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Missing user in initData")
    tg_user = json.loads(user_json)
    telegram_id = int(tg_user["id"])

    if telegram_id not in settings.allowed_telegram_id_set:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not whitelisted")

    name = " ".join(filter(None, [tg_user.get("first_name"), tg_user.get("last_name")])) or "Без имени"
    user = await get_or_create_user(session, telegram_id=telegram_id, name=name)

    token = create_access_token(user_id=user.id, telegram_id=user.telegram_id)
    return TelegramAuthResponse(access_token=token, name=user.name)
