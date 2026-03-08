from nl_processing.core.models import Language
import pytest

from nl_processing.translate_text.service import TextTranslator


@pytest.mark.asyncio
async def test_full_translation_pipeline() -> None:
    """E2e: translate multi-paragraph Dutch markdown and verify non-empty output."""
    dutch_text = (
        "# Introductie\n\n"
        "Nederland is een klein maar **dichtbevolkt** land in West-Europa.\n\n"
        "## Geografie\n\n"
        "Het land ligt grotendeels *onder zeeniveau* en wordt beschermd door dijken.\n\n"
        "## Cultuur\n\n"
        "De Nederlanders staan bekend om hun:\n\n"
        "- Tolerantie\n"
        "- Directheid\n"
        "- Liefde voor fietsen"
    )

    translator = TextTranslator(source_language=Language.NL, target_language=Language.RU)
    result = await translator.translate(dutch_text)

    assert isinstance(result, str)
    assert len(result.strip()) > 0, "Translation pipeline should produce non-empty output"


@pytest.mark.asyncio
async def test_empty_input_handling() -> None:
    """E2e: verify translate('') returns ''."""
    translator = TextTranslator(source_language=Language.NL, target_language=Language.RU)
    result = await translator.translate("")

    assert result == "", f"Expected empty string for empty input, got: '{result}'"


@pytest.mark.asyncio
async def test_markdown_heavy_input() -> None:
    """E2e: translate markdown-heavy Dutch text and verify markdown symbols present."""
    dutch_markdown = (
        "# Hoofdstuk 1\n\n"
        "## Sectie 1.1\n\n"
        "Dit is een **vetgedrukt** en *cursief* woord.\n\n"
        "### Subsectie\n\n"
        "- Punt een\n"
        "- Punt twee\n"
        "  - Sub punt\n"
        "- Punt drie"
    )

    translator = TextTranslator(source_language=Language.NL, target_language=Language.RU)
    result = await translator.translate(dutch_markdown)

    assert isinstance(result, str)
    assert "#" in result, f"Heading markdown missing from output: {result}"
    assert "**" in result, f"Bold markdown missing from output: {result}"
    assert "- " in result, f"List markdown missing from output: {result}"


@pytest.mark.asyncio
async def test_short_sentence_translation() -> None:
    """E2e: translate a simple Dutch sentence, verify non-empty string."""
    translator = TextTranslator(source_language=Language.NL, target_language=Language.RU)
    result = await translator.translate("Goede morgen, hoe gaat het?")

    assert isinstance(result, str)
    assert len(result.strip()) > 0, "Short sentence should produce non-empty translation"


def test_unsupported_pair_raises_at_init() -> None:
    """E2e: verify unsupported pair raises ValueError at init time."""
    with pytest.raises(ValueError, match="Unsupported language pair"):
        TextTranslator(source_language=Language.RU, target_language=Language.NL)
