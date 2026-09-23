from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.models import Conversation, DoctorQuestion, Message, QuestionStatus


async def get_or_create_conversation(session: AsyncSession, *, patient_id: int, user_id: int) -> Conversation:
    """One ongoing conversation per user for now — multiple named chats are a Mini App feature."""
    stmt = (
        select(Conversation)
        .where(Conversation.patient_id == patient_id, Conversation.user_id == user_id)
        .order_by(Conversation.id.desc())
        .limit(1)
    )
    conversation = (await session.execute(stmt)).scalar_one_or_none()
    if conversation is not None:
        return conversation

    conversation = Conversation(patient_id=patient_id, user_id=user_id)
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    return conversation


async def toggle_pin(session: AsyncSession, message_id: int) -> bool | None:
    message = await session.get(Message, message_id)
    if message is None:
        return None
    message.pinned = not message.pinned
    await session.commit()
    return message.pinned


async def add_doctor_question(
    session: AsyncSession, *, patient_id: int, text: str, source_message_id: int | None
) -> DoctorQuestion:
    question = DoctorQuestion(
        patient_id=patient_id, text=text, source_message_id=source_message_id, status=QuestionStatus.open
    )
    session.add(question)
    await session.commit()
    await session.refresh(question)
    return question


async def list_open_questions(session: AsyncSession, patient_id: int) -> list[DoctorQuestion]:
    stmt = (
        select(DoctorQuestion)
        .where(DoctorQuestion.patient_id == patient_id, DoctorQuestion.status == QuestionStatus.open)
        .order_by(DoctorQuestion.id)
    )
    return list((await session.execute(stmt)).scalars())
