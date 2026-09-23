from datetime import date

from pydantic import BaseModel, ConfigDict


class TreatmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    regimen: str
    cycle_no: int | None
    start_date: date
    end_date: date | None
    notes: str | None


class TreatmentCreate(BaseModel):
    regimen: str
    cycle_no: int | None = None
    start_date: date
    end_date: date | None = None
    notes: str | None = None
