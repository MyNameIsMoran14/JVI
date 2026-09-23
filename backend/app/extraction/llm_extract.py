import json

from app.core.config import settings
from app.extraction.schemas import LabReport
from app.llm.client import get_llm_client

SYSTEM_PROMPT = """Ты извлекаешь показатели из бланка лабораторного анализа крови/мочи.
Верни ТОЛЬКО JSON, без пояснений и markdown, строго по схеме:
{schema}

Правила:
- Не придумывай значения. Если показателя нет на бланке — не включай его в items.
- raw_name — название показателя ровно как написано на бланке (на языке бланка).
- ref_low/ref_high — референсные значения, напечатанные на этом же бланке рядом с показателем. Если их нет — null.
- Для качественных результатов (например, «не обнаружено», «отрицательно», «<0.1») заполняй value_text,
  а value оставляй null.
- taken_at — дата взятия анализа, если видна на бланке, в формате YYYY-MM-DD, иначе null.
- В тексте бланка может быть обрезан или отсутствовать блок с ФИО/датой рождения пациента — это ожидаемо,
  не пытайся восстановить эти данные и не включай их в ответ."""


async def extract_lab_report(*, text: str | None = None, image_b64: str | None = None) -> LabReport:
    """Calls the LLM adapter with a structured-output prompt and returns a validated LabReport.

    Uses plain `json_object` mode (not provider-specific structured outputs) since the app
    is provider-agnostic and proxies (ProxyAPI/AITUNNEL) vary in what they support — the schema
    is instead spelled out in the prompt, and Pydantic validates the result on our side.
    """
    if not text and not image_b64:
        raise ValueError("extract_lab_report needs either text or image_b64")

    schema = json.dumps(LabReport.model_json_schema(), ensure_ascii=False)
    system = SYSTEM_PROMPT.format(schema=schema)

    content: list[dict] = []
    if text:
        content.append({"type": "text", "text": text})
    if image_b64:
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}})

    model = settings.llm_vision_model if image_b64 else settings.llm_model
    client = get_llm_client()
    response = await client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": content},
        ],
    )
    raw = response.choices[0].message.content
    if raw is None:
        raise ValueError("LLM returned an empty response")
    return LabReport.model_validate_json(raw)
