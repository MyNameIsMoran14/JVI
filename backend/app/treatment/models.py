from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Treatment(Base):
    __tablename__ = "treatments"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    regimen: Mapped[str] = mapped_column(String(200))
    cycle_no: Mapped[int | None] = mapped_column()
    start_date: Mapped[date] = mapped_column(Date())
    end_date: Mapped[date | None] = mapped_column(Date())
    notes: Mapped[str | None] = mapped_column(Text())
