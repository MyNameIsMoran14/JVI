import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class DocumentKind(str, enum.Enum):
    lab = "lab"
    discharge = "discharge"
    imaging = "imaging"
    other = "other"


class DocumentStatus(str, enum.Enum):
    uploaded = "uploaded"
    parsing = "parsing"
    needs_review = "needs_review"
    confirmed = "confirmed"
    failed = "failed"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    kind: Mapped[DocumentKind] = mapped_column(Enum(DocumentKind, native_enum=False, length=20))
    file_path: Mapped[str] = mapped_column(String(500))
    mime: Mapped[str] = mapped_column(String(100))
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    taken_at: Mapped[date | None] = mapped_column(Date())
    lab_name: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, native_enum=False, length=20), default=DocumentStatus.uploaded
    )
    raw_text: Mapped[str | None] = mapped_column(Text())
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
