from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.patient.models import Patient


async def get_or_create_default_patient(session: AsyncSession) -> Patient:
    """This is a single-patient app — there is always exactly one `patients` row."""
    result = await session.execute(select(Patient).order_by(Patient.id).limit(1))
    patient = result.scalar_one_or_none()
    if patient is not None:
        return patient

    patient = Patient(full_name="Пациент")
    session.add(patient)
    await session.commit()
    await session.refresh(patient)
    return patient
