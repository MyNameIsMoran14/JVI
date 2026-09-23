from collections.abc import AsyncGenerator, Callable
from pathlib import Path

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.db import Base

# Import every domain's models so Base.metadata is fully populated before create_all.
from app.auth import models as _auth_models  # noqa: F401
from app.patient import models as _patient_models  # noqa: F401
from app.documents import models as _documents_models  # noqa: F401
from app.extraction import models as _extraction_models  # noqa: F401
from app.visits import models as _visits_models  # noqa: F401
from app.treatment import models as _treatment_models  # noqa: F401
from app.assistant import models as _assistant_models  # noqa: F401


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
