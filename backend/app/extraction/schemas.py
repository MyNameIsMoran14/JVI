from datetime import date

from pydantic import BaseModel


class LabItem(BaseModel):
    raw_name: str
    value: float | None = None
    value_text: str | None = None  # «не обнаружено», «<0.1»
    unit: str | None = None
    ref_low: float | None = None
    ref_high: float | None = None


class LabReport(BaseModel):
    taken_at: date | None = None
    lab_name: str | None = None
    items: list[LabItem] = []
