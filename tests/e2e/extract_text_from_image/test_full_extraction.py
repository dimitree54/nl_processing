import pathlib

import cv2
import numpy
import pytest

from nl_processing.core.exceptions import TargetLanguageNotFoundError, UnsupportedImageFormatError
from nl_processing.extract_text_from_image.benchmark import evaluate_extraction, generate_test_image
from nl_processing.extract_text_from_image.service import ImageTextExtractor

_FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


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
    cv2.putText(img, "Nederland is een mooi land", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)

    for ext in [".png", ".jpg", ".webp"]:
        path = str(tmp_path / f"test{ext}")
        cv2.imwrite(path, img)
        extractor = ImageTextExtractor()
        await extractor.extract_from_path(path)


@pytest.mark.asyncio
async def test_real_photo_dutch_vocabulary_extraction() -> None:
    """E2e: extract Dutch vocabulary from a real photo of a textbook page."""
    image_path = str(_FIXTURES_DIR / "dutch_vocabulary.jpg")
    ground_truth = (
        "vandaan\n"
        "veranderen\n"
        "verbeteren\n"
        "vlakbij\n"
        "volgorde, de\n"
        "voorbeeld, het\n"
        "voornaam, de\n"
        "vorm, de\n"
        "vraag, de\n"
        "vriendin, de\n"
        "vrouw, de\n"
        "wat\n"
        "week, de\n"
        "welkom\n"
        "werken\n"
        "wonen"
    )

    extractor = ImageTextExtractor()
    result = await extractor.extract_from_path(image_path)

    assert evaluate_extraction(result, ground_truth)


@pytest.mark.asyncio
async def test_real_photo_rotated_dutch_english_extraction() -> None:
    """E2e: extract only Dutch from a rotated textbook page with Dutch and English columns."""
    image_path = str(_FIXTURES_DIR / "dutch_vocabulary_rotated.jpg")
    ground_truth = (
        "klein\n"
        "kloppen\n"
        "komen\n"
        "land, het\n"
        "luisteren\n"
        "maken\n"
        "man, de\n"
        "medecursist, de\n"
        "meneer, de\n"
        "met\n"
        "mevrouw, de\n"
        "mijn\n"
        "naam, de\n"
        "naar\n"
        "nationaliteit, de\n"
        "nazeggen\n"
        "nee\n"
        "neutraal\n"
        "niet\n"
        "nieuw"
    )

    extractor = ImageTextExtractor()
    result = await extractor.extract_from_path(image_path)

    assert evaluate_extraction(result, ground_truth)


@pytest.mark.asyncio
async def test_real_photo_dutch_product_box_extraction() -> None:
    """E2e: extract Dutch text from a product packaging photo (De Ruijter hagelslag)."""
    image_path = str(_FIXTURES_DIR / "dutch_product_box.jpg")
    ground_truth = (
        "Met De Ruijter kunt u elke dag genieten "
        "van een breed assortiment smakelijke producten.\n"
        "Chocoladevlokken Melk en Puur\n"
        "Chocoladehagel Melk en Puur\n"
        "Vruchtenhagel\n"
        "Anijshagel\n"
        "Vlokfeest\n"
        "Gestampte Muisjes\n"
        "Rose en Witte Muisjes\n"
        "Blauwe en Witte Muisjes"
    )

    extractor = ImageTextExtractor()
    result = await extractor.extract_from_path(image_path)

    assert evaluate_extraction(result, ground_truth)
