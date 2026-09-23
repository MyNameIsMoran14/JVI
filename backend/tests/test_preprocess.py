from io import BytesIO

from PIL import Image

from app.extraction.preprocess import crop_header, strip_header_lines


def test_crop_header_removes_top_slice() -> None:
    image = Image.new("RGB", (100, 200), color="white")
    buffer = BytesIO()
    image.save(buffer, format="JPEG")

    cropped_bytes = crop_header(buffer.getvalue())
    cropped = Image.open(BytesIO(cropped_bytes))

    assert cropped.size[0] == 100
    assert cropped.size[1] < 200


def test_strip_header_lines_drops_first_lines() -> None:
    text = "\n".join(f"line{i}" for i in range(10))
    result = strip_header_lines(text, n=4)
    assert result.splitlines()[0] == "line4"
    assert len(result.splitlines()) == 6
