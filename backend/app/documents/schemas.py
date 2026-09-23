from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    mime: str
    taken_at: date | None
    lab_name: str | None
    status: str
    created_at: datetime


class LabResultRead(BaseModel):
    id: int
    analyte_code: str
    analyte_name: str
    value: float | None
    value_text: str | None
    unit: str | None
    ref_low: float | None
    ref_high: float | None
    flag: str | None
    confirmed: bool
