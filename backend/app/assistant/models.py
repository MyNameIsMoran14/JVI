import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, JSONVariant


class QuestionStatus(str, enum.Enum):
    open = "open"
    asked = "asked"
    answered = "answered"


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class DoctorQuestion(Base):
    __tablename__ = "doctor_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    text: Mapped[str] = mapped_column(Text())
    source_message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id"))
    status: Mapped[QuestionStatus] = mapped_column(
        Enum(QuestionStatus, native_enum=False, length=20), default=QuestionStatus.open
    )
    answer: Mapped[str | None] = mapped_column(Text())
    visit_id: Mapped[int | None] = mapped_column(ForeignKey("visits.id"))


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole, native_enum=False, length=20))
    content: Mapped[str] = mapped_column(Text())
    context_snapshot: Mapped[dict | None] = mapped_column(JSONVariant)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PatientSummary(Base):
    __tablename__ = "patient_summary"

    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), primary_key=True)
    text: Mapped[str] = mapped_column(Text())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
