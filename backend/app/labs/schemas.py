from datetime import date

from pydantic import BaseModel


class LatestLabValue(BaseModel):
    code: str
    name_ru: str
    unit: str | None
    value: float | None
    value_text: str | None
    taken_at: date
    flag: str | None
    change_pct: float | None
    previous_value: float | None


class LabSeriesPoint(BaseModel):
    taken_at: date
    value: float | None
    value_text: str | None
    flag: str | None


class LabSeries(BaseModel):
    code: str
    name_ru: str
    unit: str | None
    points: list[LabSeriesPoint]
