import asyncio
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session_maker
from app.extraction.models import Analyte

SEED_PATH = Path(__file__).resolve().parents[2] / "seeds" / "analytes.yaml"


async def seed_analytes(session: AsyncSession, seed_path: Path = SEED_PATH) -> tuple[int, int]:
    """Upsert `analytes` from seeds/analytes.yaml. Returns (created, updated)."""
    entries = yaml.safe_load(seed_path.read_text(encoding="utf-8"))

    created = updated = 0
    for entry in entries:
        result = await session.execute(select(Analyte).where(Analyte.code == entry["code"]))
        analyte = result.scalar_one_or_none()
        if analyte is None:
            session.add(Analyte(**entry))
            created += 1
            continue

        for field, value in entry.items():
            setattr(analyte, field, value)
        updated += 1

    await session.commit()
    return created, updated


async def main() -> None:
    async with async_session_maker() as session:
        created, updated = await seed_analytes(session)
    print(f"analytes: создано {created}, обновлено {updated}")


if __name__ == "__main__":
    asyncio.run(main())
