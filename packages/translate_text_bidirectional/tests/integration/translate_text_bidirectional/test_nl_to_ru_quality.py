import re
import time

from nl_processing.core.models import Language
import pytest

from nl_processing.translate_text_bidirectional.service import BidirectionalTextTranslator

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
async def test_nl_to_ru_output_cleanliness() -> None:
    """BT-FR4: NL→RU bidirectional output must not contain LLM chatter prefixes."""
    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    result = await translator.translate("Vandaag is het een prachtige dag voor een wandeling door het bos.")

    assert isinstance(result, str)
    assert len(result.strip()) > 0, "Translation should not be empty"

    for prefix in LLM_CHATTER_PREFIXES:
        assert not result.startswith(prefix), f"Output starts with LLM chatter prefix: '{prefix}'"


@pytest.mark.asyncio
async def test_nl_to_ru_cyrillic_only_output() -> None:
    """Success Criteria: NL→RU output contains only Cyrillic characters (no Latin) for text without proper nouns."""
    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    result = await translator.translate("De kat zit op de mat en kijkt naar de vogels buiten.")

    assert isinstance(result, str)
    assert len(result.strip()) > 0, "Translation should not be empty"
    assert not re.search(r"[a-zA-Z]", result), f"Latin characters found in: {result}"


@pytest.mark.asyncio
async def test_nl_to_ru_markdown_structure_preservation() -> None:
    """BT-FR2: NL→RU markdown formatting must be preserved in translation."""
    dutch_markdown = (
        "# Bidirectionele Vertaalinformatie\n\n"
        "Dit betreft een **cruciaal** bericht met *belangrijke* gegevens.\n\n"
        "- Primair element\n"
        "- Secundair onderdeel\n"
        "- Tertiair component"
    )

    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    result = await translator.translate(dutch_markdown)

    assert isinstance(result, str)
    assert result.startswith("#"), f"Heading formatting not preserved in bidirectional translation. Output: {result}"
    assert "**" in result, f"Bold markdown formatting not preserved in bidirectional translation. Output: {result}"
    assert "- " in result, f"List item formatting not preserved in bidirectional translation. Output: {result}"


@pytest.mark.asyncio
async def test_performance_nl_to_ru() -> None:
    """BT-NFR1: NL→RU translation of ~100 words must complete in <5 seconds."""
    dutch_text = (
        "Het Koninkrijk der Nederlanden is een fascinerend land in West-Europa. "
        "Dit land is wereldberoemd om zijn karakteristieke windmolens, kleurrijke tulpenvelden en fietscultuur. "
        "De vriendelijke inwoners communiceren vaak in verschillende internationale talen. "
        "Amsterdam, de bruisende hoofdstad, trekt jaarlijks miljoenen bezoekers aan. "
        "Het Nederlandse erfgoed omvat eeuwen van rijke geschiedenis en culturele tradities. "
        "De gevarieerde lokale keuken biedt heerlijke kaasspecialiteiten en verse zeevruchten. "
        "Het wisselvallige klimaat varieert van bewolkte dagen tot zonnige periodes. "
        "Nederlanders zijn gepassioneerd over voetbal en traditioneel schaatsen op natuurijs. "
        "Het onderwijssysteem staat bekend om zijn hoge kwaliteit en toegankelijkheid. "
        "De florissante economie herbergt talrijke multinationaal opererende ondernemingen."
    )

    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)

    start_timestamp = time.time()
    result = await translator.translate(dutch_text)
    execution_duration = time.time() - start_timestamp

    assert isinstance(result, str)
    assert len(result.strip()) > 0, "Bidirectional translation should not be empty"
    assert execution_duration < 5, (
        f"Bidirectional translation took {execution_duration:.2f}s — exceeds 5.00s performance threshold"
    )


@pytest.mark.asyncio
async def test_non_dutch_or_russian_text_returns_empty() -> None:
    """BT-FR8: Non-Dutch/Russian text should return empty string."""
    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    result = await translator.translate("The quick brown fox jumps over the lazy dog.")

    assert result == "", f"Expected empty string for non-Dutch/Russian input, got: '{result}'"
