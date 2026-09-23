from collections.abc import AsyncGenerator, Callable
from pathlib import Path

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

import app.core.all_models  # noqa: F401
from app.core.db import Base


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
