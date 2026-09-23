from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.context import compute_key_trends
from app.assistant.models import PatientSummary
from app.core.config import settings
from app.llm.client import get_llm_client
from app.patient.models import Patient
from app.treatment.models import Treatment
from app.visits.models import Visit

MAX_OUTPUT_TOKENS = 2000

SUMMARY_PROMPT = """Ты составляешь краткую сводку истории болезни пациента с множественной миеломой
для внутреннего использования AI-помощником семьи (сама сводка нигде не показывается пациенту
напрямую — это рабочая память помощника). Уложись примерно в 1500 токенов, пиши по делу,
ничего не придумывай — используй только блок ДАННЫЕ.

Готовые цифры и проценты в блоке ДАННЫЕ уже посчитаны — просто используй их как есть,
не пересчитывай.

Структура: диагноз и стадия, текущее лечение, ключевая динамика анализов, значимые визиты."""


async def rebuild_patient_summary(session: AsyncSession, patient_id: int) -> None:
    """Rewrites patient_summary from current data. Called after a document gets confirmed."""
    patient = await session.get(Patient, patient_id)
    if patient is None:
        return

    trends = await compute_key_trends(session, patient_id)
    treatments = list(
        (
            await session.execute(
                select(Treatment)
                .where(Treatment.patient_id == patient_id)
                .order_by(Treatment.start_date.desc())
                .limit(3)
            )
        ).scalars()
    )
    visits = list(
        (
            await session.execute(
                select(Visit).where(Visit.patient_id == patient_id).order_by(Visit.date.desc()).limit(5)
            )
        ).scalars()
    )

    data_lines: list[str] = []
    if patient.diagnosis:
        data_lines.append(f"Диагноз: {patient.diagnosis}")
    if patient.stage:
        data_lines.append(f"Стадия: {patient.stage}")
    if patient.paraprotein_type:
        data_lines.append(f"Тип парапротеина: {patient.paraprotein_type}")
    for treatment in treatments:
        cycle = f", цикл {treatment.cycle_no}" if treatment.cycle_no else ""
        data_lines.append(f"Лечение: {treatment.regimen}{cycle}, начало {treatment.start_date.strftime('%d.%m.%Y')}")
    for line in trends:
        data_lines.append(f"Анализ: {line}")
    for visit in visits:
        entry = f"Визит {visit.date.strftime('%d.%m.%Y')}"
        if visit.doctor:
            entry += f", {visit.doctor}"
        if visit.summary:
            entry += f": {visit.summary}"
        data_lines.append(entry)

    if not data_lines:
        return  # nothing to summarize yet — don't call the LLM for an empty record

    client = get_llm_client()
    response = await client.chat.completions.create(
        model=settings.llm_model,
        max_completion_tokens=MAX_OUTPUT_TOKENS,
        messages=[
            {"role": "system", "content": SUMMARY_PROMPT},
            {"role": "user", "content": "ДАННЫЕ:\n" + "\n".join(data_lines)},
        ],
    )
    text = response.choices[0].message.content
    if not text:
        return

    summary = await session.get(PatientSummary, patient_id)
    if summary is None:
        session.add(PatientSummary(patient_id=patient_id, text=text.strip()))
    else:
        summary.text = text.strip()
    await session.commit()
