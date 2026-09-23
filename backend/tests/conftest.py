from collections.abc import AsyncGenerator
from pathlib import Path

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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
async def session(tmp_path: Path) -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db_session:
        yield db_session

    await engine.dispose()
