from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.documents.models import Document
from app.extraction.models import Analyte, LabResult, ResultFlag

# Thresholds live here, not hardcoded per-value logic scattered around — CLAUDE.md rule 5:
# reference ranges come off the lab form itself, only these red-flag thresholds are config,
# and they're meant to be reviewed with the treating hematologist.
LAB_OUT_OF_RANGE_CODES = {"CALCIUM_TOTAL", "CALCIUM_ION", "CREATININE"}
LAB_SHARP_DROP_RULES: dict[str, float] = {"HGB": 0.20, "NEUT": 0.30, "PLT": 0.30}

TEXT_RED_FLAG_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("температура на фоне химиотерапии", ("температур", "жар", "озноб", "лихорадк")),
    ("сильная боль в спине", ("боль в спине", "болит спина", "спину скрутило")),
    ("слабость или онемение в ногах", ("онемен", "не чувствую ног", "слабость в ног", "отказали ноги")),
    ("спутанность сознания", ("спутанность", "заторможен", "не узнаёт", "теряет сознание", "потерял сознание")),
    ("кровотечение", ("кровотечение", "кровоточ", "кровь идёт", "кровь из")),
    ("резкое уменьшение мочи", ("не мочится", "мало мочи", "перестал писать", "не писает")),
]

RED_FLAG_TEMPLATE = (
    "⚠️ Есть сигналы, при которых стоит как можно скорее связаться с лечащим врачом или "
    "вызвать скорую, а не ждать ответа здесь:\n{flags}\n\n"
    "Дальше — пояснение, но не откладывайте звонок врачу из-за него."
)


async def _latest_confirmed(
    session: AsyncSession, patient_id: int, analyte_id: int, limit: int
) -> list[LabResult]:
    stmt = (
        select(LabResult)
        .join(Document, Document.id == LabResult.document_id)
        .where(
            Document.patient_id == patient_id,
            LabResult.analyte_id == analyte_id,
            LabResult.confirmed.is_(True),
        )
        .order_by(LabResult.taken_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars())


async def check_lab_red_flags(session: AsyncSession, patient_id: int) -> list[str]:
    """Code-computed, per CLAUDE.md rule 1 — the model never decides this on its own."""
    flags: list[str] = []
    codes = LAB_OUT_OF_RANGE_CODES | set(LAB_SHARP_DROP_RULES)
    analytes = {
        a.code: a for a in (await session.execute(select(Analyte).where(Analyte.code.in_(codes)))).scalars()
    }

    for code in LAB_OUT_OF_RANGE_CODES:
        analyte = analytes.get(code)
        if analyte is None:
            continue
        latest = await _latest_confirmed(session, patient_id, analyte.id, limit=1)
        if latest and latest[0].flag in (ResultFlag.low, ResultFlag.high) and latest[0].value is not None:
            direction = "ниже" if latest[0].flag == ResultFlag.low else "выше"
            unit = f" {latest[0].unit}" if latest[0].unit else ""
            flags.append(f"{analyte.name_ru} {direction} референсных значений ({latest[0].value:g}{unit})")

    for code, threshold in LAB_SHARP_DROP_RULES.items():
        analyte = analytes.get(code)
        if analyte is None:
            continue
        recent = await _latest_confirmed(session, patient_id, analyte.id, limit=2)
        if len(recent) < 2:
            continue
        newest, previous = recent[0], recent[1]
        if newest.value is None or previous.value is None or previous.value <= 0:
            continue
        drop = (previous.value - newest.value) / previous.value
        if drop >= threshold:
            flags.append(
                f"{analyte.name_ru} резко снизился: {previous.value:g} → {newest.value:g} "
                f"(с {previous.taken_at.strftime('%d.%m.%Y')})"
            )

    return flags


def check_text_red_flags(question: str) -> list[str]:
    normalized = question.lower()
    return [label for label, keywords in TEXT_RED_FLAG_RULES if any(kw in normalized for kw in keywords)]


def format_red_flag_notice(flags: list[str]) -> str:
    return RED_FLAG_TEMPLATE.format(flags="\n".join(f"• {flag}" for flag in flags))
