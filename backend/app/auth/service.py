from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User, UserRole


async def get_or_create_user(session: AsyncSession, *, telegram_id: int, name: str) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    user = User(telegram_id=telegram_id, name=name, role=UserRole.editor)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
