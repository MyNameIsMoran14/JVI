import enum
from datetime import date

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, JSONVariant


class ResultFlag(str, enum.Enum):
    low = "L"
    high = "H"
    normal = "N"


class Analyte(Base):
    __tablename__ = "analytes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name_ru: Mapped[str] = mapped_column(String(200))
    canonical_unit: Mapped[str | None] = mapped_column(String(30))
    aliases: Mapped[list[str]] = mapped_column(JSONVariant, default=list)
    group: Mapped[str] = mapped_column(String(100))
    is_key: Mapped[bool] = mapped_column(Boolean, default=False)


class UnitConversion(Base):
    __tablename__ = "unit_conversions"
    __table_args__ = (UniqueConstraint("analyte_id", "from_unit"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    analyte_id: Mapped[int] = mapped_column(ForeignKey("analytes.id"), index=True)
    from_unit: Mapped[str] = mapped_column(String(30))
    factor: Mapped[float] = mapped_column(Numeric(18, 6))


class LabResult(Base):
    __tablename__ = "lab_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    analyte_id: Mapped[int] = mapped_column(ForeignKey("analytes.id"), index=True)
    taken_at: Mapped[date] = mapped_column(Date(), index=True)
    value: Mapped[float | None] = mapped_column(Numeric(18, 6))
    value_text: Mapped[str | None] = mapped_column(String(100))
    unit: Mapped[str | None] = mapped_column(String(30))
    value_canonical: Mapped[float | None] = mapped_column(Numeric(18, 6))
    ref_low: Mapped[float | None] = mapped_column(Numeric(18, 6))
    ref_high: Mapped[float | None] = mapped_column(Numeric(18, 6))
    flag: Mapped[ResultFlag | None] = mapped_column(Enum(ResultFlag, native_enum=False, length=10))
    raw_name: Mapped[str] = mapped_column(String(200))
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
