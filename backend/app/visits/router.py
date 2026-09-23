from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.db import get_session
from app.patient.service import get_or_create_default_patient
from app.visits.models import Visit
from app.visits.schemas import VisitCreate, VisitRead

router = APIRouter(prefix="/visits", tags=["visits"])


@router.get("", response_model=list[VisitRead])
async def list_visits(
    session: AsyncSession = Depends(get_session), _user: User = Depends(get_current_user)
) -> list[VisitRead]:
    patient = await get_or_create_default_patient(session)
    stmt = select(Visit).where(Visit.patient_id == patient.id).order_by(Visit.date.desc())
    visits = list((await session.execute(stmt)).scalars())
    return [VisitRead.model_validate(v) for v in visits]


@router.post("", response_model=VisitRead)
async def create_visit(
    body: VisitCreate,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> VisitRead:
    patient = await get_or_create_default_patient(session)
    visit = Visit(patient_id=patient.id, **body.model_dump())
    session.add(visit)
    await session.commit()
    await session.refresh(visit)
    return VisitRead.model_validate(visit)
