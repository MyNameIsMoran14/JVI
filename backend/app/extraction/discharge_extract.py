from app.core.config import settings
from app.llm.client import get_llm_client

MAX_OUTPUT_TOKENS = 4096

TRANSCRIBE_PROMPT = """Ты внимательно переписываешь весь видимый текст с фото или скана
медицинского документа (выписка, заключение врача). Задача — точная построчная
транскрипция, а не пересказ: сохраняй структуру (разделы, абзацы), ничего не сокращай
и не обобщай.

Если в верхней части виден блок с ФИО пациента и датой рождения — пропусти эти строки,
остальной текст переписывай полностью. Верни только сам текст документа, без вступлений
и комментариев от себя."""


async def transcribe_image(image_b64: str) -> str:
    client = get_llm_client()
    response = await client.chat.completions.create(
        model=settings.llm_vision_model,
        max_completion_tokens=MAX_OUTPUT_TOKENS,
        messages=[
            {"role": "system", "content": TRANSCRIBE_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                ],
            },
        ],
    )
    text = response.choices[0].message.content
    if not text:
        raise ValueError("LLM returned an empty transcription")
    return text.strip()
