import re
import time

import pytest

from nl_processing.core.models import Language
from nl_processing.translate_text.service import TextTranslator

LLM_CHATTER_PREFIXES = [
    "Here is",
    "Translation:",
    "Sure,",
    "Of course",
    "The translation",
    "Below is",
    "Certainly",
]


@pytest.mark.asyncio
async def test_output_cleanliness() -> None:
    """TT-FR4: Output must not contain LLM chatter prefixes."""
    translator = TextTranslator(source_language=Language.NL, target_language=Language.RU)
    result = await translator.translate("Het is een mooie dag om te wandelen in het park.")

    assert isinstance(result, str)
    assert len(result.strip()) > 0, "Translation should not be empty"

    for prefix in LLM_CHATTER_PREFIXES:
        assert not result.startswith(prefix), f"Output starts with LLM chatter prefix: '{prefix}'"


@pytest.mark.asyncio
async def test_cyrillic_only_output() -> None:
    """Success Criteria: Output contains only Cyrillic characters (no Latin) for text without proper nouns."""
    translator = TextTranslator(source_language=Language.NL, target_language=Language.RU)
    result = await translator.translate("De kat zit op de mat en kijkt naar de vogels buiten.")

    assert isinstance(result, str)
    assert len(result.strip()) > 0, "Translation should not be empty"
    assert not re.search(r"[a-zA-Z]", result), f"Latin characters found in: {result}"


@pytest.mark.asyncio
async def test_markdown_structure_preservation() -> None:
    """TT-FR2: Markdown formatting must be preserved in translation."""
    dutch_markdown = (
        "# Belangrijke informatie\n\n"
        "Dit is een **belangrijk** bericht met *cursieve* tekst.\n\n"
        "- Eerste punt\n"
        "- Tweede punt\n"
        "- Derde punt"
    )

    translator = TextTranslator(source_language=Language.NL, target_language=Language.RU)
    result = await translator.translate(dutch_markdown)

    assert isinstance(result, str)
    assert result.startswith("#"), f"Heading not preserved. Output: {result}"
    assert "**" in result, f"Bold markdown not preserved. Output: {result}"
    assert "- " in result, f"List items not preserved. Output: {result}"


@pytest.mark.asyncio
async def test_performance() -> None:
    """TT-NFR1: Translation of ~100 words must complete in <5 seconds."""
    dutch_text = (
        "Nederland is een prachtig land in West-Europa. "
        "Het staat bekend om zijn windmolens, tulpen en fietsen. "
        "De mensen zijn vriendelijk en spreken vaak meerdere talen. "
        "Amsterdam is de hoofdstad en trekt veel toeristen aan. "
        "Het land heeft een rijke geschiedenis en cultuur. "
        "De Nederlandse keuken is gevarieerd met veel kaas en vis. "
        "Het weer is vaak bewolkt maar soms schijnt de zon. "
        "De Nederlanders houden van voetbal en schaatsen. "
        "Het onderwijs is van hoge kwaliteit en toegankelijk. "
        "De economie is sterk en er zijn veel internationale bedrijven."
    )

    translator = TextTranslator(source_language=Language.NL, target_language=Language.RU)

    start = time.time()
    result = await translator.translate(dutch_text)
    elapsed = time.time() - start

    assert isinstance(result, str)
    assert len(result.strip()) > 0, "Translation should not be empty"
    assert elapsed < 5, f"Translation took {elapsed:.2f}s — exceeds 5.00s QA gate"


@pytest.mark.asyncio
async def test_non_dutch_text_returns_empty() -> None:
    """TT-FR8: Non-Dutch text should return empty string."""
    translator = TextTranslator(source_language=Language.NL, target_language=Language.RU)
    result = await translator.translate("The quick brown fox jumps over the lazy dog.")

    assert result == "", f"Expected empty string for non-Dutch input, got: '{result}'"
