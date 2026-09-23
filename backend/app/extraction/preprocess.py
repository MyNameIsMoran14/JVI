import base64
from io import BytesIO

import pdfplumber
from pdf2image import convert_from_bytes
from PIL import Image

# Lab letterheads put ФИО/дата рождения in the top portion of the page — cropping it out
# before the image reaches the (external) vision model is the MVP privacy measure from
# CLAUDE.md rule 3. It's a blunt heuristic, not layout detection.
HEADER_CROP_RATIO = 0.18
HEADER_LINE_COUNT = 4

MIN_TEXT_LAYER_CHARS = 40


def crop_header(image_bytes: bytes) -> bytes:
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    width, height = image.size
    top = int(height * HEADER_CROP_RATIO)
    cropped = image.crop((0, top, width, height))
    buffer = BytesIO()
    cropped.save(buffer, format="JPEG")
    return buffer.getvalue()


def image_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("ascii")


def strip_header_lines(text: str, n: int = HEADER_LINE_COUNT) -> str:
    return "\n".join(text.splitlines()[n:])


def pdf_first_page_text(content: bytes) -> str | None:
    """Returns the text layer of the first page, or None if the PDF looks like a scan."""
    with pdfplumber.open(BytesIO(content)) as pdf:
        if not pdf.pages:
            return None
        text = pdf.pages[0].extract_text() or ""
    return text if len(text.strip()) >= MIN_TEXT_LAYER_CHARS else None


def pdf_first_page_image(content: bytes) -> bytes:
    images = convert_from_bytes(content, first_page=1, last_page=1, dpi=200)
    buffer = BytesIO()
    images[0].save(buffer, format="JPEG")
    return buffer.getvalue()
