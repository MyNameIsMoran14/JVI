import json

from app.core.config import settings
from app.extraction.schemas import LabReport
from app.llm.client import get_llm_client

MAX_OUTPUT_TOKENS = 8000

SYSTEM_PROMPT = """Ты извлекаешь показатели из бланка лабораторного анализа крови/мочи/иммунограммы.
Бланк может быть большим: несколько разделов, по 10-30 строк каждый. Твоя задача — извлечь
КАЖДУЮ строку из КАЖДОГО раздела, без исключений. Это самое важное правило: не останавливайся
после первого раздела и не выбирай только «главные» или самые узнаваемые показатели — если
на бланке 25 строк, в ответе должно быть 25 элементов, а не 3-5.

Порядок работы:
1. Пройди по изображению (или тексту) сверху вниз, раздел за разделом.
2. Для каждого раздела перечисли ВСЕ строки таблицы, включая малоизвестные и узкоспециальные
   показатели (например, подтипы лимфоцитов с CD-маркерами) — если не уверен, что означает
   показатель, всё равно включи его как есть, с тем названием, что написано на бланке.
3. Прежде чем закончить, ещё раз сверься с изображением и проверь, что не пропустил ни одной
   строки ни в одном разделе.

Верни ТОЛЬКО JSON, без пояснений и markdown, строго по схеме:
{schema}

Правила по полям:
- raw_name — название показателя ровно как написано на бланке, включая пометки в скобках
  (например, «CD3+CD19-» или «(отн.)» / «(абс.)» — это разные строки, извлекай их отдельно).
- Не придумывай значения. Если строка не помещается или совсем не видна — не включай её,
  но не пропускай видимые строки.
- ref_low/ref_high — референсные значения, напечатанные на этом же бланке рядом с показателем.
  Если их нет — null.
- Для качественных результатов (например, «не обнаружено», «отрицательно», «<0.1») заполняй
  value_text, а value оставляй null.
- taken_at — дата взятия анализа, если видна на бланке, в формате YYYY-MM-DD, иначе null.
- Если бланк прислан несколькими изображениями (страницами) — это один документ, объедини
  показатели со всех страниц в один список items.
- В тексте бланка может быть обрезан или отсутствовать блок с ФИО/датой рождения пациента —
  это ожидаемо, не пытайся восстановить эти данные и не включай их в ответ."""


async def extract_lab_report(*, text: str | None = None, images_b64: list[str] | None = None) -> LabReport:
    """Calls the LLM adapter with a structured-output prompt and returns a validated LabReport.

    Uses plain `json_object` mode (not provider-specific structured outputs) since the app
    is provider-agnostic and proxies (ProxyAPI/AITUNNEL) vary in what they support — the schema
    is instead spelled out in the prompt, and Pydantic validates the result on our side.
    """
    if not text and not images_b64:
        raise ValueError("extract_lab_report needs either text or images_b64")

    schema = json.dumps(LabReport.model_json_schema(), ensure_ascii=False)
    system = SYSTEM_PROMPT.format(schema=schema)

    content: list[dict] = []
    if text:
        content.append({"type": "text", "text": text})
    for image_b64 in images_b64 or []:
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}})

    model = settings.llm_vision_model if images_b64 else settings.llm_model
    client = get_llm_client()
    response = await client.chat.completions.create(
        model=model,
        max_tokens=MAX_OUTPUT_TOKENS,
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
