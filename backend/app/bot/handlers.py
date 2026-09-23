from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.auth.service import get_or_create_user
from app.core.db import async_session_maker
from app.documents.models import DocumentKind
from app.documents.service import save_document
from app.patient.service import get_or_create_default_patient

router = Router()

WELCOME_TEXT = (
    "Привет! Я медицинский помощник семьи.\n\n"
    "Пришлите фото или PDF анализа — я его сохраню.\n"
    "Распознавание показателей и чат с AI-помощником появятся на следующих этапах."
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

    if created:
        await message.answer(
            f"Файл сохранён (#{document.id}). "
            "Автоматическое распознавание показателей добавим на следующем этапе."
        )
    else:
        await message.answer("Этот файл уже был загружен раньше.")


@router.message(F.text)
async def handle_text(message: Message) -> None:
    await message.answer(
        "Чат с AI-помощником появится на следующем этапе. "
        "Пока можно присылать фото или PDF анализов."
    )
