from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.context import build_context, load_system_prompt
from app.assistant.models import Message, MessageRole
from app.assistant.red_flags import check_lab_red_flags, check_text_red_flags, format_red_flag_notice
from app.core.config import settings
from app.llm.client import get_llm_client

HISTORY_MESSAGE_LIMIT = 20
MAX_OUTPUT_TOKENS = 2000

FALLBACK_ANSWER = "Не получилось получить ответ от помощника, попробуйте ещё раз через минуту."


async def _recent_messages(session: AsyncSession, conversation_id: int) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(HISTORY_MESSAGE_LIMIT)
    )
    result = await session.execute(stmt)
    return list(reversed(list(result.scalars())))


async def ask_assistant(
    session: AsyncSession, *, conversation_id: int, patient_id: int, question: str
) -> Message:
    """Runs one chat turn: red flags, context, LLM call, persists both messages.

    Returns the saved assistant `Message` row (so the caller can attach pin/ask-doctor buttons
    without a second query).
    """
    lab_flags = await check_lab_red_flags(session, patient_id)
    text_flags = check_text_red_flags(question)
    all_flags = lab_flags + text_flags

    context_block = await build_context(session, patient_id)
    system_prompt = f"{load_system_prompt()}\n\n=== КОНТЕКСТ ===\n{context_block}"

    history = await _recent_messages(session, conversation_id)

    llm_messages = [{"role": "system", "content": system_prompt}]
    for m in history:
        role = "user" if m.role == MessageRole.user else "assistant"
        llm_messages.append({"role": role, "content": m.content})
    llm_messages.append({"role": "user", "content": question})

    try:
        client = get_llm_client()
        response = await client.chat.completions.create(
            model=settings.llm_model,
            max_completion_tokens=MAX_OUTPUT_TOKENS,
            messages=llm_messages,
        )
        answer = response.choices[0].message.content or FALLBACK_ANSWER
    except Exception:
        answer = FALLBACK_ANSWER

    if all_flags and answer != FALLBACK_ANSWER:
        answer = format_red_flag_notice(all_flags) + "\n\n" + answer

    session.add(Message(conversation_id=conversation_id, role=MessageRole.user, content=question))
    assistant_message = Message(
        conversation_id=conversation_id,
        role=MessageRole.assistant,
        content=answer,
        context_snapshot={"context": context_block, "red_flags": all_flags},
    )
    session.add(assistant_message)
    await session.commit()
    await session.refresh(assistant_message)
    return assistant_message
