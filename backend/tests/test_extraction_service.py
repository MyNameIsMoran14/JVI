from sqlalchemy.ext.asyncio import AsyncSession

from app.extraction.service import get_or_create_unmatched_analyte


async def test_get_or_create_unmatched_analyte_creates_new(session: AsyncSession) -> None:
    analyte = await get_or_create_unmatched_analyte(session, "Странный показатель", "ммоль/л")
    await session.commit()

    assert analyte.name_ru == "Странный показатель"
    assert analyte.canonical_unit == "ммоль/л"
    assert analyte.aliases == ["Странный показатель"]
    assert analyte.group == "auto"
    assert analyte.is_key is False


async def test_get_or_create_unmatched_analyte_reuses_existing(session: AsyncSession) -> None:
    first = await get_or_create_unmatched_analyte(session, "Странный показатель", "ммоль/л")
    await session.commit()

    second = await get_or_create_unmatched_analyte(session, "Странный показатель", "ммоль/л")
    await session.commit()

    assert first.id == second.id
