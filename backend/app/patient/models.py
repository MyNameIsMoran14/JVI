from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, JSONVariant


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200))
    birth_year: Mapped[int | None] = mapped_column()
    diagnosis: Mapped[str | None] = mapped_column(Text())
    diagnosis_date: Mapped[date | None] = mapped_column(Date())
    stage: Mapped[str | None] = mapped_column(String(50))
    paraprotein_type: Mapped[str | None] = mapped_column(String(50))
    comorbidities: Mapped[list[str]] = mapped_column(JSONVariant, default=list)
    allergies: Mapped[list[str]] = mapped_column(JSONVariant, default=list)
    notes: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
