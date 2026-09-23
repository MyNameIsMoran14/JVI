from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant import chat as chat_module
from app.assistant.models import Conversation, Message, MessageRole
from app.auth.models import User, UserRole
from app.patient.models import Patient


class _FakeCompletions:
    def __init__(self, content: str) -> None:
        self._content = content

    async def create(self, **kwargs):  # noqa: ANN003, ANN201
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self._content))])


class _FakeClient:
    def __init__(self, content: str) -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions(content))


async def _make_conversation(session: AsyncSession) -> Conversation:
    patient = Patient(full_name="Тестовый пациент")
    user = User(telegram_id=1, name="Тест", role=UserRole.editor)
    session.add_all([patient, user])
    await session.commit()
    await session.refresh(patient)
    await session.refresh(user)

    conversation = Conversation(patient_id=patient.id, user_id=user.id)
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    return conversation


async def test_ask_assistant_saves_messages_and_returns_answer(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    conversation = await _make_conversation(session)
    monkeypatch.setattr(chat_module, "get_llm_client", lambda: _FakeClient("Ответ помощника."))

    result = await chat_module.ask_assistant(
        session, conversation_id=conversation.id, patient_id=conversation.patient_id, question="Как дела с анализами?"
    )

    assert result.content == "Ответ помощника."
    assert result.role == MessageRole.assistant

    messages = list(
        (await session.execute(select(Message).where(Message.conversation_id == conversation.id))).scalars()
    )
    assert len(messages) == 2
    assert any(m.role == MessageRole.user and m.content == "Как дела с анализами?" for m in messages)
    assert any(m.role == MessageRole.assistant and m.content == "Ответ помощника." for m in messages)


async def test_ask_assistant_prepends_red_flag_notice(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    conversation = await _make_conversation(session)
    monkeypatch.setattr(chat_module, "get_llm_client", lambda: _FakeClient("Обычный ответ."))

    result = await chat_module.ask_assistant(
        session,
        conversation_id=conversation.id,
        patient_id=conversation.patient_id,
        question="У него сильная боль в спине и температура после химии",
    )

    assert "⚠️" in result.content
    assert "Обычный ответ." in result.content


async def test_ask_assistant_falls_back_on_llm_error(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    conversation = await _make_conversation(session)

    class _BoomClient:
        chat = SimpleNamespace(completions=SimpleNamespace())

    async def _boom(**kwargs):  # noqa: ANN003, ANN201
        raise RuntimeError("boom")

    client = _BoomClient()
    client.chat.completions.create = _boom
    monkeypatch.setattr(chat_module, "get_llm_client", lambda: client)

    result = await chat_module.ask_assistant(
        session, conversation_id=conversation.id, patient_id=conversation.patient_id, question="Привет"
    )

    assert result.content == chat_module.FALLBACK_ANSWER
