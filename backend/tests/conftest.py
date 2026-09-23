from collections.abc import AsyncGenerator, Callable
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

import app.core.all_models  # noqa: F401
from app.core.db import Base, get_session


@pytest_asyncio.fixture
async def db_engine(tmp_path: Path) -> AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
def db_session_maker(db_engine: AsyncEngine) -> Callable[[], AsyncSession]:
    return async_sessionmaker(db_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def session(db_session_maker: Callable[[], AsyncSession]) -> AsyncGenerator[AsyncSession, None]:
    async with db_session_maker() as db_session:
        yield db_session


@pytest_asyncio.fixture
async def api_client(db_session_maker: Callable[[], AsyncSession]) -> AsyncGenerator[AsyncClient, None]:
    """An httpx client against the real FastAPI app, with `Depends(get_session)` overridden
    to the sqlite test fixture instead of the real Postgres engine."""
    from app.main import app as fastapi_app

    async def _override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with db_session_maker() as db_session:
            yield db_session

    fastapi_app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    fastapi_app.dependency_overrides.pop(get_session, None)


@pytest_asyncio.fixture
async def authed_headers(
    db_session_maker: Callable[[], AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> dict[str, str]:
    """A whitelisted, logged-in user for API tests that don't care which telegram_id it is."""
    from app.auth.jwt import create_access_token
    from app.auth.models import User, UserRole
    from app.core.config import settings as app_settings

    telegram_id = 111
    async with db_session_maker() as db_session:
        user = User(telegram_id=telegram_id, name="Тест", role=UserRole.editor)
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

    monkeypatch.setattr(app_settings, "allowed_telegram_ids", str(telegram_id))
    token = create_access_token(user_id=user.id, telegram_id=telegram_id)
    return {"Authorization": f"Bearer {token}"}
