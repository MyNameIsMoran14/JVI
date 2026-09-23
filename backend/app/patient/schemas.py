from datetime import date

from pydantic import BaseModel, ConfigDict


class PatientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    birth_year: int | None
    diagnosis: str | None
    diagnosis_date: date | None
    stage: str | None
    paraprotein_type: str | None
    comorbidities: list[str]
    allergies: list[str]
    notes: str | None


class PatientUpdate(BaseModel):
    full_name: str | None = None
    birth_year: int | None = None
    diagnosis: str | None = None
    diagnosis_date: date | None = None
    stage: str | None = None
    paraprotein_type: str | None = None
    comorbidities: list[str] | None = None
    allergies: list[str] | None = None
    notes: str | None = None
