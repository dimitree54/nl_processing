import pathlib
import re
import time

from nl_processing.core.exceptions import TargetLanguageNotFoundInInputError
from nl_processing.core.image_encoding import generate_test_image
from nl_processing.core.models import Language
import pytest

from nl_processing.translate_text_from_image.service import ImageTextTranslator

UNWANTED_PREFIXES = ["Here is", "Translation:", "Sure,", "Of course", "The translation", "Below is", "Certainly"]


@pytest.mark.asyncio
async def test_synthetic_feature_matrix_translation_quality(tmp_path: pathlib.Path) -> None:
    """One synthetic image call should cover content, Cyrillic output, line breaks, chatter-free output, and latency."""
    feature_matrix_text = "Het regent vandaag\nDit is een test"
    image_file = str(tmp_path / "feature_matrix.png")
    generate_test_image(feature_matrix_text, image_file, width=700, height=180)

    translator = ImageTextTranslator(source_language=Language.NL, target_language=Language.RU)

    start = time.perf_counter()
    result = await translator.translate_from_path(image_file)
    elapsed = time.perf_counter() - start

    assert result.strip(), "Translation should produce non-empty output"
    assert re.search(r"[а-яёА-ЯЁ]", result), f"Expected Cyrillic characters in Russian translation: {result}"
    assert "\n" in result, f"Line breaks should be preserved in translation: {result}"
    for prefix in UNWANTED_PREFIXES:
        assert not result.startswith(prefix), f"Output contains unwanted prefix '{prefix}': {result}"
    assert elapsed < 10, f"Translation took {elapsed:.2f}s, exceeds 10s limit"


@pytest.mark.asyncio
async def test_mixed_language_image_translates_dutch_only(tmp_path: pathlib.Path) -> None:
    """Ensures only Dutch text gets translated from mixed Dutch-Russian image."""
    # Create image with Dutch and Russian text
    mixed_content = "Goede reis\nСчастливого пути"
    image_file = str(tmp_path / "mixed_language.png")
    generate_test_image(mixed_content, image_file, width=650, height=180)

    # Initialize translator
    translator = ImageTextTranslator(source_language=Language.NL, target_language=Language.RU)

    # Execute translation
    result_text = await translator.translate_from_path(image_file)

    # Validate translation output
    assert isinstance(result_text, str)
    assert len(result_text.strip()) > 0, "Should translate Dutch portion"

    # Check for travel-related Russian words (translation of "Goede reis")
    travel_indicators = ["путеш", "поезд", "счастлив", "добр", "дорог"]
    has_travel_term = any(indicator in result_text.lower() for indicator in travel_indicators)
    assert has_travel_term, f"Expected travel-related translation of 'Goede reis': {result_text}"

    # Verify original Russian text is not copied verbatim
    assert "Счастливого пути" not in result_text, f"Original Russian text should not appear: {result_text}"


@pytest.mark.asyncio
async def test_english_only_image_raises_language_error(tmp_path: pathlib.Path) -> None:
    """Validates that English-only text triggers TargetLanguageNotFoundInInputError."""
    # Create English text image
    english_content = "Remember to charge your phone before leaving tomorrow"
    image_file = str(tmp_path / "english_only.png")
    generate_test_image(english_content, image_file, width=750, height=120)

    # Setup translator for Dutch detection
    translator = ImageTextTranslator(source_language=Language.NL, target_language=Language.RU)

    # Verify exception is raised for non-Dutch content
    with pytest.raises(TargetLanguageNotFoundInInputError):
        await translator.translate_from_path(image_file)
