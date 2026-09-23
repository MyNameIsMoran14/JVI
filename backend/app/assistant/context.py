from datetime import date
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.models import DoctorQuestion, PatientSummary, QuestionStatus
from app.documents.models import Document
from app.extraction.models import Analyte, LabResult
from app.patient.models import Patient
from app.treatment.models import Treatment
from app.visits.models import Visit

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "assistant.md"


@lru_cache
def load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


async def compute_key_trends(session: AsyncSession, patient_id: int) -> list[str]:
    """Ready-to-read trend strings for key analytes — the model never computes these itself
    (CLAUDE.md rule 1): "κ/λ: 12,4 → 8,1 (−35% за 2 мес.)" style lines, built in Python."""
    key_analytes = list(
        (await session.execute(select(Analyte).where(Analyte.is_key.is_(True)))).scalars()
    )
    lines: list[str] = []

    for analyte in key_analytes:
        stmt = (
            select(LabResult)
            .join(Document, Document.id == LabResult.document_id)
            .where(
                Document.patient_id == patient_id,
                LabResult.analyte_id == analyte.id,
                LabResult.confirmed.is_(True),
            )
            .order_by(LabResult.taken_at.desc())
            .limit(5)
        )
        recent = list((await session.execute(stmt)).scalars())
        if not recent:
            continue
        recent = list(reversed(recent))  # oldest -> newest

        latest = recent[-1]
        value_str = f"{latest.value:g}" if latest.value is not None else (latest.value_text or "—")
        unit_str = f" {latest.unit}" if latest.unit else ""
        line = f"{analyte.name_ru}: {value_str}{unit_str} ({latest.taken_at.strftime('%d.%m.%Y')})"

        first = recent[0]
        if len(recent) >= 2 and first.value and latest.value is not None:
            change_pct = (latest.value - first.value) / first.value * 100
            days = (latest.taken_at - first.taken_at).days
            period = f"{days} дн." if days < 60 else f"{days // 30} мес."
            arrow = "↑" if change_pct > 0 else ("↓" if change_pct < 0 else "→")
            line += f" {arrow} {change_pct:+.0f}% за {period} (было {first.value:g}{unit_str})"

        lines.append(line)

    return lines


async def build_context(session: AsyncSession, patient_id: int) -> str:
    """Assembles the per-request context block described in docs/PROJECT_SPEC.md, section 7.

    ФИО and exact birth date never enter this text — only a derived age — per CLAUDE.md rule 3.
    """
    parts: list[str] = []
    patient = await session.get(Patient, patient_id)

    if patient is not None:
        age = date.today().year - patient.birth_year if patient.birth_year else None
        card = [f"Пациент{f', {age} лет' if age else ''}."]
        if patient.diagnosis:
            card.append(f"Диагноз: {patient.diagnosis}.")
        if patient.stage:
            card.append(f"Стадия: {patient.stage}.")
        if patient.paraprotein_type:
            card.append(f"Тип парапротеина: {patient.paraprotein_type}.")
        if patient.comorbidities:
            card.append(f"Сопутствующие заболевания: {', '.join(patient.comorbidities)}.")
        if patient.allergies:
            card.append(f"Аллергии: {', '.join(patient.allergies)}.")
        parts.append("КАРТОЧКА ПАЦИЕНТА:\n" + " ".join(card))

    treatment = (
        await session.execute(
            select(Treatment)
            .where(Treatment.patient_id == patient_id)
            .order_by(Treatment.start_date.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if treatment is not None:
        cycle = f", цикл {treatment.cycle_no}" if treatment.cycle_no else ""
        parts.append(
            "ТЕКУЩЕЕ ЛЕЧЕНИЕ:\n"
            f"Схема: {treatment.regimen}{cycle}, с {treatment.start_date.strftime('%d.%m.%Y')}."
        )

    summary = await session.get(PatientSummary, patient_id)
    if summary is not None and summary.text:
        parts.append("ИСТОРИЯ БОЛЕЗНИ:\n" + summary.text)

    trends = await compute_key_trends(session, patient_id)
    if trends:
        parts.append("АНАЛИЗЫ (ключевые показатели):\n" + "\n".join(f"- {line}" for line in trends))

    visit = (
        await session.execute(
            select(Visit).where(Visit.patient_id == patient_id).order_by(Visit.date.desc()).limit(1)
        )
    ).scalar_one_or_none()
    if visit is not None:
        line = visit.date.strftime("%d.%m.%Y")
        if visit.doctor:
            line += f", врач {visit.doctor}"
        if visit.summary:
            line += f": {visit.summary}"
        parts.append("ПОСЛЕДНИЙ ВИЗИТ:\n" + line)

    open_questions = list(
        (
            await session.execute(
                select(DoctorQuestion)
                .where(DoctorQuestion.patient_id == patient_id, DoctorQuestion.status == QuestionStatus.open)
                .order_by(DoctorQuestion.id.desc())
                .limit(10)
            )
        ).scalars()
    )
    if open_questions:
        parts.append("ОТКРЫТЫЕ ВОПРОСЫ К ВРАЧУ:\n" + "\n".join(f"- {q.text}" for q in open_questions))

    return "\n\n".join(parts) if parts else "Данных о пациенте пока нет."
