from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import decode_access_token
from app.auth.models import User
from app.core.config import settings
from app.core.db import get_session

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing token")

    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc

    # Defense in depth: re-check the whitelist even though initData verification already
    # gated token issuance — a telegram_id removed from ALLOWED_TELEGRAM_IDS loses access
    # immediately, without waiting for the token to expire.
    if payload["telegram_id"] not in settings.allowed_telegram_id_set:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not whitelisted")

    user = await session.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user
