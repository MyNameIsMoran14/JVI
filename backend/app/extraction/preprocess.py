import base64
from io import BytesIO

import pdfplumber
from pdf2image import convert_from_bytes
from PIL import Image

# Lab letterheads put ФИО/дата рождения in the top portion of the page — cropping it out
# before the image reaches the (external) vision model is the MVP privacy measure from
# CLAUDE.md rule 3. It's a blunt heuristic, not layout detection.
HEADER_CROP_RATIO = 0.13
HEADER_LINE_COUNT = 4

MIN_TEXT_LAYER_CHARS = 40
MAX_PDF_PAGES = 6
PDF_RENDER_DPI = 260
# Pillow's default JPEG quality (75) blurs dense lab tables enough to lose rows when a
# vision model reads them — bump it for anything we re-encode before sending to the LLM.
JPEG_QUALITY = 92


def crop_header(image_bytes: bytes) -> bytes:
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    width, height = image.size
    top = int(height * HEADER_CROP_RATIO)
    cropped = image.crop((0, top, width, height))
    buffer = BytesIO()
    cropped.save(buffer, format="JPEG", quality=JPEG_QUALITY)
    return buffer.getvalue()


def image_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("ascii")


def strip_header_lines(text: str, n: int = HEADER_LINE_COUNT) -> str:
    return "\n".join(text.splitlines()[n:])


def pdf_text(content: bytes) -> str | None:
    """Text layer across all pages, or None if the PDF looks like a scan."""
    with pdfplumber.open(BytesIO(content)) as pdf:
        texts = [page.extract_text() or "" for page in pdf.pages]
    combined = "\n".join(texts).strip()
    return combined if len(combined) >= MIN_TEXT_LAYER_CHARS else None


def pdf_page_images(content: bytes, max_pages: int = MAX_PDF_PAGES) -> list[bytes]:
    """Renders up to `max_pages` pages to JPEG — a scanned multi-page report needs all of them."""
    images = convert_from_bytes(content, first_page=1, last_page=max_pages, dpi=PDF_RENDER_DPI)
    rendered = []
    for image in images:
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=JPEG_QUALITY)
        rendered.append(buffer.getvalue())
    return rendered
