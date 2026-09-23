from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.db import get_session
from app.patient.service import get_or_create_default_patient
from app.treatment.models import Treatment
from app.treatment.schemas import TreatmentCreate, TreatmentRead

router = APIRouter(prefix="/treatments", tags=["treatments"])


@router.get("", response_model=list[TreatmentRead])
async def list_treatments(
    session: AsyncSession = Depends(get_session), _user: User = Depends(get_current_user)
) -> list[TreatmentRead]:
    patient = await get_or_create_default_patient(session)
    stmt = select(Treatment).where(Treatment.patient_id == patient.id).order_by(Treatment.start_date.desc())
    treatments = list((await session.execute(stmt)).scalars())
    return [TreatmentRead.model_validate(t) for t in treatments]


@router.post("", response_model=TreatmentRead)
async def create_treatment(
    body: TreatmentCreate,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> TreatmentRead:
    patient = await get_or_create_default_patient(session)
    treatment = Treatment(patient_id=patient.id, **body.model_dump())
    session.add(treatment)
    await session.commit()
    await session.refresh(treatment)
    return TreatmentRead.model_validate(treatment)
