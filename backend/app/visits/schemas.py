from datetime import date

from pydantic import BaseModel, ConfigDict


class VisitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    doctor: str | None
    clinic: str | None
    summary: str | None
    decisions: str | None
    next_visit_date: date | None


class VisitCreate(BaseModel):
    date: date
    doctor: str | None = None
    clinic: str | None = None
    summary: str | None = None
    decisions: str | None = None
    next_visit_date: date | None = None
