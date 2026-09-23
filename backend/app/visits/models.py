import datetime

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    # Named `date` on purpose, but that means later annotations in this class body must use
    # `datetime.date` (not a bare `date` import) — the column attribute shadows it otherwise
    # and SQLAlchemy silently infers NOT NULL for `next_visit_date` instead of nullable.
    date: Mapped[datetime.date] = mapped_column(Date(), index=True)
    doctor: Mapped[str | None] = mapped_column(String(200))
    clinic: Mapped[str | None] = mapped_column(String(200))
    summary: Mapped[str | None] = mapped_column(Text())
    decisions: Mapped[str | None] = mapped_column(Text())
    next_visit_date: Mapped[datetime.date | None] = mapped_column(Date())
