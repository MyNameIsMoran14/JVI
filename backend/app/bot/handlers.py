from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from app.auth.service import get_or_create_user
from app.core.db import async_session_maker
from app.core.queue import get_arq_pool
from app.documents.models import DocumentKind
from app.documents.service import save_document
from app.extraction.service import confirm_document, discard_document
from app.patient.service import get_or_create_default_patient

router = Router()

WELCOME_TEXT = (
    "Привет! Я медицинский помощник семьи.\n\n"
    "Пришлите фото или PDF анализа — я его сохраню и распознаю показатели.\n"
    "Чат с AI-помощником появится на следующем этапе."
)


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
            kind=DocumentKind.lab,
            filename=filename,
            mime=mime,
            content=content,
        )

    if not created:
        await message.answer("Этот файл уже был загружен раньше.")
        return

    await message.answer(f"Файл сохранён (#{document.id}). Распознаю, это ~30 сек.")
    pool = await get_arq_pool()
    try:
        await pool.enqueue_job("parse_document", document.id)
    finally:
        await pool.aclose()


@router.message(F.text)
async def handle_text(message: Message) -> None:
    await message.answer(
        "Чат с AI-помощником появится на следующем этапе. "
        "Пока можно присылать фото или PDF анализов."
    )


@router.callback_query(F.data.startswith("confirm_doc:"))
async def handle_confirm(callback: CallbackQuery) -> None:
    if callback.data is None:
        return
    document_id = int(callback.data.split(":", 1)[1])
    async with async_session_maker() as session:
        count = await confirm_document(session, document_id)
    await callback.answer("Сохранено")
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
