from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from app.assistant.chat import ask_assistant
from app.assistant.models import Conversation, Message as AssistantMessage, MessageRole
from app.assistant.service import (
    add_doctor_question,
    get_or_create_conversation,
    list_open_questions,
    toggle_pin,
)
from app.assistant.summary import rebuild_patient_summary
from app.auth.service import get_or_create_user
from app.core.db import async_session_maker
from app.core.queue import get_arq_pool
from app.documents.models import Document, DocumentKind
from app.documents.service import save_document
from app.extraction.service import confirm_document, discard_document
from app.patient.service import get_or_create_default_patient

router = Router()

WELCOME_TEXT = (
    "Привет! Я медицинский помощник семьи.\n\n"
    "Пришлите фото или PDF анализа или выписки — я его сохраню и распознаю.\n"
    "Любой другой текст — вопрос AI-помощнику, он знает историю болезни и анализы.\n"
    "«Вопросы к врачу» — список того, что накопилось спросить на приёме."
)

CLASSIFY_KEYBOARD_TEMPLATE = "Что за файл?"
QUESTIONS_TRIGGERS = {"/questions", "вопросы к врачу", "вопросы врачу", "вопросы"}


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    await message.answer(WELCOME_TEXT)


@router.message(F.photo | F.document)
async def handle_file(message: Message) -> None:
    if message.from_user is None or message.bot is None:
        return

    if message.photo:
        tg_file = message.photo[-1]
        filename = f"{tg_file.file_unique_id}.jpg"
        mime = "image/jpeg"
    elif message.document:
        tg_file = message.document
        filename = tg_file.file_name or tg_file.file_unique_id
        mime = tg_file.mime_type or "application/octet-stream"
    else:
        return

    file_info = await message.bot.get_file(tg_file.file_id)
    if file_info.file_path is None:
        await message.answer("Не получилось скачать файл, попробуйте ещё раз.")
        return
    buffer = await message.bot.download_file(file_info.file_path)
    if buffer is None:
        await message.answer("Не получилось скачать файл, попробуйте ещё раз.")
        return
    content = buffer.read()

    async with async_session_maker() as session:
        user = await get_or_create_user(
            session, telegram_id=message.from_user.id, name=message.from_user.full_name
        )
        patient = await get_or_create_default_patient(session)
        document, created = await save_document(
            session,
            patient_id=patient.id,
            uploaded_by=user.id,
            kind=DocumentKind.other,  # classified below, once the user picks a button
            filename=filename,
            mime=mime,
            content=content,
        )

    if not created:
        await message.answer("Этот файл уже был загружен раньше.")
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Анализы", callback_data=f"classify_doc:lab:{document.id}"),
                InlineKeyboardButton(text="📄 Выписка", callback_data=f"classify_doc:discharge:{document.id}"),
            ]
        ]
    )
    await message.answer(
        f"Файл сохранён (#{document.id}). {CLASSIFY_KEYBOARD_TEMPLATE}", reply_markup=keyboard
    )


@router.message(Command("questions"))
@router.message(F.text.func(lambda text: text.strip().lower() in QUESTIONS_TRIGGERS))
async def handle_list_questions(message: Message) -> None:
    async with async_session_maker() as session:
        patient = await get_or_create_default_patient(session)
        questions = await list_open_questions(session, patient.id)

    if not questions:
        await message.answer("Открытых вопросов к врачу пока нет.")
        return

    lines = ["Вопросы к врачу:"] + [f"{i}. {q.text}" for i, q in enumerate(questions, start=1)]
    await message.answer("\n".join(lines))


@router.message(F.text)
async def handle_text(message: Message) -> None:
    if message.from_user is None or message.bot is None or not message.text:
        return

    await message.bot.send_chat_action(message.chat.id, "typing")

    async with async_session_maker() as session:
        user = await get_or_create_user(
            session, telegram_id=message.from_user.id, name=message.from_user.full_name
        )
        patient = await get_or_create_default_patient(session)
        conversation = await get_or_create_conversation(session, patient_id=patient.id, user_id=user.id)
        assistant_message = await ask_assistant(
            session, conversation_id=conversation.id, patient_id=patient.id, question=message.text
        )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📌 Закрепить", callback_data=f"pin_msg:{assistant_message.id}"),
                InlineKeyboardButton(
                    text="➕ В вопросы врачу", callback_data=f"ask_doctor:{assistant_message.id}"
                ),
            ]
        ]
    )
    await message.answer(assistant_message.content, reply_markup=keyboard)


@router.callback_query(F.data.startswith("classify_doc:"))
async def handle_classify(callback: CallbackQuery) -> None:
    if callback.data is None:
        return
    _, kind_value, document_id_str = callback.data.split(":", 2)
    document_id = int(document_id_str)

    task_name = "parse_document" if kind_value == "lab" else "parse_discharge"
    doc_kind = DocumentKind.lab if kind_value == "lab" else DocumentKind.discharge

    async with async_session_maker() as session:
        document = await session.get(Document, document_id)
        if document is None:
            await callback.answer("Файл не найден")
            return
        document.kind = doc_kind
        await session.commit()

    await callback.answer()
    pool = await get_arq_pool()
    try:
        await pool.enqueue_job(task_name, document_id)
    finally:
        await pool.aclose()

    if callback.message and isinstance(callback.message, Message):
        label = "анализы" if kind_value == "lab" else "выписку"
        await callback.message.edit_text(
            f"{callback.message.text}\n\nРаспознаю как {label}, это ~30 сек.", reply_markup=None
        )


@router.callback_query(F.data.startswith("confirm_doc:"))
async def handle_confirm(callback: CallbackQuery) -> None:
    if callback.data is None:
        return
    document_id = int(callback.data.split(":", 1)[1])
    # Answer first — rebuilding patient_summary below calls the LLM and can take a few
    # seconds, longer than Telegram is happy to leave a callback tap unacknowledged.
    await callback.answer("Сохранено")

    async with async_session_maker() as session:
        count = await confirm_document(session, document_id)
        document = await session.get(Document, document_id)
        if document is not None:
            await rebuild_patient_summary(session, document.patient_id)

    if callback.message and isinstance(callback.message, Message):
        await callback.message.edit_text(
            f"{callback.message.text}\n\n✅ Сохранено ({count} показателей).", reply_markup=None
        )


@router.callback_query(F.data.startswith("discard_doc:"))
async def handle_discard(callback: CallbackQuery) -> None:
    if callback.data is None:
        return
    document_id = int(callback.data.split(":", 1)[1])
    async with async_session_maker() as session:
        await discard_document(session, document_id)
    await callback.answer("Удалено")
    if callback.message and isinstance(callback.message, Message):
        await callback.message.edit_text(f"{callback.message.text}\n\n🗑 Не сохранено.", reply_markup=None)


@router.callback_query(F.data.startswith("pin_msg:"))
async def handle_pin(callback: CallbackQuery) -> None:
    if callback.data is None:
        return
    message_id = int(callback.data.split(":", 1)[1])
    async with async_session_maker() as session:
        pinned = await toggle_pin(session, message_id)
    if pinned is None:
        await callback.answer("Сообщение не найдено")
    else:
        await callback.answer("Закреплено" if pinned else "Откреплено")


@router.callback_query(F.data.startswith("ask_doctor:"))
async def handle_ask_doctor(callback: CallbackQuery) -> None:
    if callback.data is None:
        return
    message_id = int(callback.data.split(":", 1)[1])

    async with async_session_maker() as session:
        assistant_message = await session.get(AssistantMessage, message_id)
        if assistant_message is None:
            await callback.answer("Сообщение не найдено")
            return
        conversation = await session.get(Conversation, assistant_message.conversation_id)
        if conversation is None:
            await callback.answer("Не получилось")
            return

        preceding_user_message = (
            await session.execute(
                select(AssistantMessage)
                .where(
                    AssistantMessage.conversation_id == assistant_message.conversation_id,
                    AssistantMessage.id < assistant_message.id,
                    AssistantMessage.role == MessageRole.user,
                )
                .order_by(AssistantMessage.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        question_text = preceding_user_message.content if preceding_user_message else assistant_message.content

        await add_doctor_question(
            session, patient_id=conversation.patient_id, text=question_text, source_message_id=message_id
        )

    await callback.answer("Добавлено в вопросы к врачу")
