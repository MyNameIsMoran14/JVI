from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.db import get_session
from app.patient.schemas import PatientRead, PatientUpdate
from app.patient.service import get_or_create_default_patient

router = APIRouter(prefix="/patient", tags=["patient"])


@router.get("", response_model=PatientRead)
async def read_patient(
    session: AsyncSession = Depends(get_session), _user: User = Depends(get_current_user)
) -> PatientRead:
    patient = await get_or_create_default_patient(session)
    return PatientRead.model_validate(patient)


@router.patch("", response_model=PatientRead)
async def update_patient(
    body: PatientUpdate,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> PatientRead:
    patient = await get_or_create_default_patient(session)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(patient, field, value)
    await session.commit()
    await session.refresh(patient)
    return PatientRead.model_validate(patient)
