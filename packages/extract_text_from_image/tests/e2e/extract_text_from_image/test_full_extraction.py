import pathlib

import pytest

from nl_processing.extract_text_from_image.service import ImageTextExtractor
from tests.helpers.text_comparison import evaluate_extraction, normalize_text

_FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


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
    expected_lines = [
        "Met De Ruijter kunt u elke dag genieten",
        "Chocoladevlokken",
        "Chocoladehagel",
        "Vruchtenhagel",
        "Anijshagel",
        "Vlokfeest",
        "Gestampte Muisjes",
        "Blauwe en Witte Muisjes",
    ]

    extractor = ImageTextExtractor()
    result = await extractor.extract_from_path(image_path)
    normalized_result = normalize_text(result)

    for line in expected_lines:
        assert normalize_text(line) in normalized_result
    assert "roze en witte muisjes" in normalized_result or "rose en witte muisjes" in normalized_result
