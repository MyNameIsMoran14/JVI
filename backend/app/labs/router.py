from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.db import get_session
from app.documents.models import Document
from app.extraction.models import Analyte, LabResult
from app.labs.schemas import LabSeries, LabSeriesPoint, LatestLabValue
from app.patient.service import get_or_create_default_patient

router = APIRouter(prefix="/labs", tags=["labs"])

SERIES_POINT_LIMIT = 30


@router.get("/latest", response_model=list[LatestLabValue])
async def latest_values(
    session: AsyncSession = Depends(get_session), _user: User = Depends(get_current_user)
) -> list[LatestLabValue]:
    patient = await get_or_create_default_patient(session)
    key_analytes = list(
        (await session.execute(select(Analyte).where(Analyte.is_key.is_(True)))).scalars()
    )

    results: list[LatestLabValue] = []
    for analyte in key_analytes:
        stmt = (
            select(LabResult)
            .join(Document, Document.id == LabResult.document_id)
            .where(
                Document.patient_id == patient.id,
                LabResult.analyte_id == analyte.id,
                LabResult.confirmed.is_(True),
            )
            .order_by(LabResult.taken_at.desc())
            .limit(2)
        )
        recent = list((await session.execute(stmt)).scalars())
        if not recent:
            continue

        latest = recent[0]
        previous = recent[1] if len(recent) > 1 else None
        change_pct = None
        if previous is not None and previous.value and latest.value is not None:
            change_pct = (latest.value - previous.value) / previous.value * 100

        results.append(
            LatestLabValue(
                code=analyte.code,
                name_ru=analyte.name_ru,
                unit=latest.unit,
                value=latest.value,
                value_text=latest.value_text,
                taken_at=latest.taken_at,
                flag=latest.flag.value if latest.flag else None,
                change_pct=change_pct,
                previous_value=previous.value if previous else None,
            )
        )

    return results


@router.get("/series", response_model=list[LabSeries])
async def series(
    codes: str = Query(..., description="Comma-separated analyte codes, e.g. HGB,FLC_RATIO"),
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> list[LabSeries]:
    patient = await get_or_create_default_patient(session)
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    if not code_list:
        return []

    analytes = list(
        (await session.execute(select(Analyte).where(Analyte.code.in_(code_list)))).scalars()
    )

    result: list[LabSeries] = []
    for analyte in analytes:
        stmt = (
            select(LabResult)
            .join(Document, Document.id == LabResult.document_id)
            .where(
                Document.patient_id == patient.id,
                LabResult.analyte_id == analyte.id,
                LabResult.confirmed.is_(True),
            )
            .order_by(LabResult.taken_at.desc())
            .limit(SERIES_POINT_LIMIT)
        )
        rows = list(reversed(list((await session.execute(stmt)).scalars())))
        result.append(
            LabSeries(
                code=analyte.code,
                name_ru=analyte.name_ru,
                unit=analyte.canonical_unit,
                points=[
                    LabSeriesPoint(
                        taken_at=r.taken_at,
                        value=r.value_canonical if r.value_canonical is not None else r.value,
                        value_text=r.value_text,
                        flag=r.flag.value if r.flag else None,
                    )
                    for r in rows
                ],
            )
        )

    return result
