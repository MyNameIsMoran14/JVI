import logging
from datetime import date
from pathlib import Path
from typing import Any

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import delete, select, update

from app.assistant.summary import rebuild_patient_summary
from app.auth.models import User
from app.core.config import settings
from app.core.db import async_session_maker
from app.documents.models import Document, DocumentStatus
from app.extraction.discharge_extract import transcribe_image
from app.extraction.llm_extract import extract_lab_report
from app.extraction.models import Analyte, LabResult, ResultFlag, UnitConversion
from app.extraction.normalize import compute_flag, convert_unit, detect_jump, match_analyte
from app.extraction.preprocess import (
    crop_header,
    image_to_base64,
    pdf_page_images,
    pdf_text,
    strip_header_lines,
)
from app.extraction.schemas import LabItem
from app.extraction.service import get_or_create_unmatched_analyte

logger = logging.getLogger(__name__)

FLAG_LABEL = {
    ResultFlag.low: "↓ ниже нормы",
    ResultFlag.high: "↑ выше нормы",
    ResultFlag.normal: "",
}

DISCHARGE_PREVIEW_CHARS = 1500


async def _latest_confirmed_canonical_value(
    session: Any, patient_id: int, analyte_id: int, before: date
) -> float | None:
    stmt = (
        select(LabResult.value_canonical)
        .join(Document, Document.id == LabResult.document_id)
        .where(
            Document.patient_id == patient_id,
            LabResult.analyte_id == analyte_id,
            LabResult.confirmed.is_(True),
            LabResult.taken_at < before,
            LabResult.value_canonical.is_not(None),
        )
        .order_by(LabResult.taken_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _notify(uploader: User | None, text: str, markup: InlineKeyboardMarkup | None = None) -> None:
    if uploader is None or not settings.telegram_bot_token:
        return
    bot = Bot(token=settings.telegram_bot_token)
    try:
        await bot.send_message(uploader.telegram_id, text, reply_markup=markup)
    finally:
        await bot.session.close()


def _format_value(item: LabItem, unit_for_display: str | None) -> str:
    if item.value is not None:
        unit = f" {unit_for_display}" if unit_for_display else ""
        return f"{item.value:g}{unit}"
    return item.value_text or "—"


async def _read_file(document: Document) -> bytes:
    return (Path(settings.files_dir) / document.file_path).read_bytes()


async def parse_document(ctx: dict, document_id: int) -> None:
    async with async_session_maker() as session:
        document = await session.get(Document, document_id)
        if document is None:
            logger.warning("parse_document: document %s not found", document_id)
            return

        uploader = await session.get(User, document.uploaded_by)
        # Idempotency: a retried/duplicated job must replace prior unconfirmed results, not add to
        # them — but never touch rows the user already confirmed.
        await session.execute(
            delete(LabResult).where(LabResult.document_id == document.id, LabResult.confirmed.is_(False))
        )
        document.status = DocumentStatus.parsing
        await session.commit()

        try:
            file_bytes = await _read_file(document)
            text: str | None = None
            images_b64: list[str] | None = None

            if document.mime == "application/pdf":
                full_text = pdf_text(file_bytes)
                if full_text:
                    text = strip_header_lines(full_text)
                else:
                    pages = pdf_page_images(file_bytes)
                    images_b64 = [
                        image_to_base64(crop_header(page) if i == 0 else page)
                        for i, page in enumerate(pages)
                    ]
            else:
                images_b64 = [image_to_base64(crop_header(file_bytes))]

            report = await extract_lab_report(text=text, images_b64=images_b64)
        except Exception:
            logger.exception("extraction failed for document %s", document_id)
            document.status = DocumentStatus.failed
            await session.commit()
            await _notify(
                uploader,
                "Не получилось распознать файл. Попробуйте прислать более чёткое фото или PDF.",
            )
            return

        analytes = list((await session.execute(select(Analyte))).scalars())
        conversions = list((await session.execute(select(UnitConversion))).scalars())
        taken_at = report.taken_at or document.taken_at or date.today()

        rows: list[tuple[Analyte, LabItem, ResultFlag | None, bool]] = []
        notes: list[str] = []

        for item in report.items:
            analyte, confidence = match_analyte(item.raw_name, analytes)
            is_new_analyte = False
            if analyte is None:
                # Nothing gets dropped — an unrecognized label becomes a new analyte instead,
                # so it's on the graph from the first time it's ever seen.
                analyte = await get_or_create_unmatched_analyte(session, item.raw_name, item.unit)
                analytes.append(analyte)
                confidence = 1.0
                is_new_analyte = True

            value_canonical: float | None = None
            if item.value is not None:
                value_canonical, issue = convert_unit(item.value, item.unit, analyte, conversions)
                if issue:
                    notes.append(f"{analyte.name_ru}: {issue}")

                previous = await _latest_confirmed_canonical_value(
                    session, document.patient_id, analyte.id, before=taken_at
                )
                if value_canonical is not None and previous is not None:
                    if detect_jump(value_canonical, previous):
                        notes.append(f"{analyte.name_ru}: резкий скачок к прошлому результату, проверьте")

            flag = compute_flag(item.value, item.ref_low, item.ref_high)

            session.add(
                LabResult(
                    document_id=document.id,
                    analyte_id=analyte.id,
                    taken_at=taken_at,
                    value=item.value,
                    value_text=item.value_text,
                    unit=item.unit,
                    value_canonical=value_canonical,
                    ref_low=item.ref_low,
                    ref_high=item.ref_high,
                    flag=flag,
                    raw_name=item.raw_name,
                    confidence=round(confidence, 3),
                    confirmed=False,
                )
            )
            rows.append((analyte, item, flag, is_new_analyte))

        document.status = DocumentStatus.needs_review
        document.lab_name = document.lab_name or report.lab_name
        document.taken_at = document.taken_at or report.taken_at
        await session.commit()

        if not rows:
            await _notify(
                uploader,
                "Не нашёл ни одного показателя на этом файле. "
                "Проверьте, что фото не обрезано и хорошо видно таблицу.",
            )
            return

        new_count = sum(1 for *_, is_new in rows if is_new)
        lines = [f"Разобрал анализ от {taken_at.strftime('%d.%m.%Y')} ({len(rows)} показателей):"]
        for analyte, item, flag, is_new_analyte in rows:
            marker = f" {FLAG_LABEL[flag]}" if flag else ""
            prefix = "🆕 " if is_new_analyte else "• "
            lines.append(f"{prefix}{analyte.name_ru}: {_format_value(item, item.unit)}{marker}")

        if new_count:
            lines.append(f"\n🆕 — новый показатель ({new_count}), добавлен в справочник впервые.")

        if notes:
            lines.append("\nОбратите внимание:")
            lines.extend(f"• {note}" for note in notes)

        # Nothing uncertain (no unit issues, no jumps, no brand-new indicators) → save outright.
        # Confirmation is only worth the tap when something actually needs a human look.
        needs_review = bool(notes) or new_count > 0
        if not needs_review:
            await session.execute(
                update(LabResult).where(LabResult.document_id == document.id).values(confirmed=True)
            )
            document.status = DocumentStatus.confirmed
            await session.commit()
            await rebuild_patient_summary(session, document.patient_id)
            lines.append("\nВсё сошлось с референсами и справочником — сохранил автоматически.")
            await _notify(uploader, "\n".join(lines))
            return

        lines.append("\nВсё верно?")
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Всё верно", callback_data=f"confirm_doc:{document.id}"),
                    InlineKeyboardButton(text="🗑 Не сохранять", callback_data=f"discard_doc:{document.id}"),
                ]
            ]
        )
        await _notify(uploader, "\n".join(lines), markup=keyboard)


async def parse_discharge(ctx: dict, document_id: int) -> None:
    """Transcribes a discharge summary / doctor's note into `document.raw_text`.

    Unlike lab reports this has no numeric fields to validate against, so there's no
    confirm/discard step — the recognized text is stored and shown straight away.
    """
    async with async_session_maker() as session:
        document = await session.get(Document, document_id)
        if document is None:
            logger.warning("parse_discharge: document %s not found", document_id)
            return

        uploader = await session.get(User, document.uploaded_by)
        document.status = DocumentStatus.parsing
        await session.commit()

        try:
            file_bytes = await _read_file(document)

            if document.mime == "application/pdf":
                full_text = pdf_text(file_bytes)
                if full_text:
                    text = strip_header_lines(full_text)
                else:
                    pages = pdf_page_images(file_bytes)
                    parts = [
                        await transcribe_image(image_to_base64(crop_header(page) if i == 0 else page))
                        for i, page in enumerate(pages)
                    ]
                    text = "\n\n".join(parts)
            else:
                text = await transcribe_image(image_to_base64(crop_header(file_bytes)))
        except Exception:
            logger.exception("discharge transcription failed for document %s", document_id)
            document.status = DocumentStatus.failed
            await session.commit()
            await _notify(
                uploader,
                "Не получилось распознать выписку. Попробуйте прислать более чёткое фото или PDF.",
            )
            return

        document.raw_text = text
        document.status = DocumentStatus.confirmed
        await session.commit()

        preview = text if len(text) <= DISCHARGE_PREVIEW_CHARS else text[:DISCHARGE_PREVIEW_CHARS] + "…"
        await _notify(uploader, f"Распознал выписку (#{document.id}):\n\n{preview}")
