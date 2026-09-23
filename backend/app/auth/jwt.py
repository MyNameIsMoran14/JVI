from datetime import UTC, datetime, timedelta
from typing import TypedDict

import jwt

from app.core.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_TTL = timedelta(days=30)


class TokenPayload(TypedDict):
    sub: str  # user id
    telegram_id: int
    exp: int


def create_access_token(*, user_id: int, telegram_id: int) -> str:
    payload: TokenPayload = {
        "sub": str(user_id),
        "telegram_id": telegram_id,
        "exp": int((datetime.now(UTC) + ACCESS_TOKEN_TTL).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> TokenPayload:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    return TokenPayload(sub=payload["sub"], telegram_id=payload["telegram_id"], exp=payload["exp"])
