import pathlib
import re
import time

from nl_processing.core.exceptions import TargetLanguageNotFoundError
from nl_processing.core.models import Language
import pytest

from nl_processing.translate_text_from_image.benchmark import render_text_image
from nl_processing.translate_text_from_image.service import ImageTextTranslator


@pytest.mark.asyncio
async def test_simple_dutch_image_produces_cyrillic_translation(tmp_path: pathlib.Path) -> None:
    """Verifies basic Dutch text in image gets translated to Cyrillic Russian."""
    # Create simple Dutch text image
    dutch_text = "Het regent vandaag in Utrecht"
    image_file = str(tmp_path / "dutch_text.png")
    render_text_image(dutch_text, image_file, image_width=700, image_height=150)

    # Configure translator for Dutch to Russian
    translator = ImageTextTranslator(source_language=Language.NL, target_language=Language.RU)

    # Execute translation
    translation_result = await translator.translate_from_path(image_file)

    # Verify output contains content
    assert isinstance(translation_result, str)
    assert len(translation_result.strip()) > 0, "Translation should produce non-empty output"

    # Verify Cyrillic characters present
    has_cyrillic = re.search(r"[а-яёА-ЯЁ]", translation_result) is not None
    assert has_cyrillic, f"Expected Cyrillic characters in Russian translation: {translation_result}"

    # Verify no Dutch words remain (Utrecht may be transliterated)
    dutch_words = ["Het", "regent", "vandaag"]
    for word in dutch_words:
        assert word not in translation_result, f"Dutch word '{word}' found in translation: {translation_result}"


@pytest.mark.asyncio
async def test_multiline_image_preserves_structure(tmp_path: pathlib.Path) -> None:
    """Confirms line breaks are maintained in multi-line Dutch text translation."""
    # Generate multi-line Dutch content
    multiline_dutch = "Dit is een test\nvan meerdere regels"
    image_file = str(tmp_path / "multiline_dutch.png")
    render_text_image(multiline_dutch, image_file, image_width=600, image_height=200)

    # Setup translator
    translator = ImageTextTranslator(source_language=Language.NL, target_language=Language.RU)

    # Perform translation
    translated_text = await translator.translate_from_path(image_file)

    # Check line structure preservation
    assert isinstance(translated_text, str)
    assert "\n" in translated_text, f"Line breaks should be preserved in translation: {translated_text}"


@pytest.mark.asyncio
async def test_mixed_language_image_translates_dutch_only(tmp_path: pathlib.Path) -> None:
    """Ensures only Dutch text gets translated from mixed Dutch-Russian image."""
    # Create image with Dutch and Russian text
    mixed_content = "Goede reis\nСчастливого пути"
    image_file = str(tmp_path / "mixed_language.png")
    render_text_image(mixed_content, image_file, image_width=650, image_height=180)

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
    """Validates that English-only text triggers TargetLanguageNotFoundError."""
    # Create English text image
    english_content = "Remember to charge your phone before leaving tomorrow"
    image_file = str(tmp_path / "english_only.png")
    render_text_image(english_content, image_file, image_width=750, image_height=120)

    # Setup translator for Dutch detection
    translator = ImageTextTranslator(source_language=Language.NL, target_language=Language.RU)

    # Verify exception is raised for non-Dutch content
    with pytest.raises(TargetLanguageNotFoundError):
        await translator.translate_from_path(image_file)


@pytest.mark.asyncio
async def test_translation_completes_within_time_limit(tmp_path: pathlib.Path) -> None:
    """Confirms translation operations complete within acceptable time bounds."""
    # Create basic Dutch text image
    simple_text = "Hallo wereld"
    image_file = str(tmp_path / "performance_test.png")
    render_text_image(simple_text, image_file, image_width=500, image_height=100)

    # Configure translator
    translator = ImageTextTranslator(source_language=Language.NL, target_language=Language.RU)

    # Measure translation timing
    start_time = time.time()
    await translator.translate_from_path(image_file)
    execution_time = time.time() - start_time

    # Validate performance requirement
    assert execution_time < 10, f"Translation took {execution_time:.2f}s, exceeds 10s limit"


@pytest.mark.asyncio
async def test_translation_output_has_no_chatter_prefixes(tmp_path: pathlib.Path) -> None:
    """Verifies translation output lacks AI assistant chatter phrases."""
    # Generate simple Dutch image
    clean_text = "De zon schijnt vandaag"
    image_file = str(tmp_path / "clean_output_test.png")
    render_text_image(clean_text, image_file, image_width=600, image_height=120)

    # Setup translator
    translator = ImageTextTranslator(source_language=Language.NL, target_language=Language.RU)

    # Get translation
    output_text = await translator.translate_from_path(image_file)

    # Check for unwanted AI chatter prefixes
    unwanted_prefixes = ["Here is", "Translation:", "Sure,", "Of course", "The translation", "Below is", "Certainly"]

    for prefix in unwanted_prefixes:
        prefix_found = output_text.startswith(prefix)
        assert not prefix_found, f"Output contains unwanted prefix '{prefix}': {output_text}"
