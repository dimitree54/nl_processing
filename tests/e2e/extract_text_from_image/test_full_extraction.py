import pathlib

import cv2
import numpy
import pytest

from nl_processing.core.exceptions import TargetLanguageNotFoundError, UnsupportedImageFormatError
from nl_processing.extract_text_from_image.benchmark import generate_test_image
from nl_processing.extract_text_from_image.service import ImageTextExtractor


@pytest.mark.asyncio
async def test_full_dutch_extraction_pipeline(tmp_path: pathlib.Path) -> None:
    """End-to-end: generate image -> extract -> verify content."""
    text = "Nederland is een mooi land"
    image_path = str(tmp_path / "e2e.png")
    generate_test_image(text, image_path, font_scale=1.5, width=800, height=100)

    extractor = ImageTextExtractor()
    result = await extractor.extract_from_path(image_path)

    assert isinstance(result, str)
    assert len(result.strip()) > 0


@pytest.mark.asyncio
async def test_unsupported_format_raises_error(tmp_path: pathlib.Path) -> None:
    """E2e: unsupported format raises UnsupportedImageFormatError immediately."""
    bmp_path = str(tmp_path / "test.bmp")
    pathlib.Path(bmp_path).write_bytes(b"fake bmp content")

    extractor = ImageTextExtractor()
    with pytest.raises(UnsupportedImageFormatError):
        await extractor.extract_from_path(bmp_path)


@pytest.mark.asyncio
async def test_blank_image_raises_target_language_not_found(tmp_path: pathlib.Path) -> None:
    """E2e: blank image with no text raises TargetLanguageNotFoundError."""
    blank = numpy.zeros((100, 400, 3), dtype=numpy.uint8)
    blank.fill(255)
    blank_path = str(tmp_path / "blank.png")
    cv2.imwrite(blank_path, blank)

    extractor = ImageTextExtractor()
    with pytest.raises(TargetLanguageNotFoundError):
        await extractor.extract_from_path(blank_path)


@pytest.mark.asyncio
async def test_supported_image_formats(tmp_path: pathlib.Path) -> None:
    """E2e: verify PNG, JPEG, WebP formats are accepted (no format error)."""
    img = numpy.zeros((100, 400, 3), dtype=numpy.uint8)
    img.fill(255)
    cv2.putText(img, "Test", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)

    for ext in [".png", ".jpg", ".webp"]:
        path = str(tmp_path / f"test{ext}")
        cv2.imwrite(path, img)
        extractor = ImageTextExtractor()
        # Should not raise UnsupportedImageFormatError
        # May raise TargetLanguageNotFoundError or return text — both are valid
        try:
            await extractor.extract_from_path(path)
        except TargetLanguageNotFoundError:
            pass  # Expected — "Test" is English, not Dutch
