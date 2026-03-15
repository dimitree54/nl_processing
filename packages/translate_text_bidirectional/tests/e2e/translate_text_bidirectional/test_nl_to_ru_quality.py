import re
import time

from nl_processing.core.models import Language
import pytest

from nl_processing.translate_text_bidirectional.service import BidirectionalTextTranslator
from tests.e2e.translate_text_bidirectional.assertions import assert_no_llm_chatter

NL_TO_RU_MARKDOWN_TEXT = (
    "# Bidirectionele vertaalinformatie\n\n"
    "Dit betreft een **cruciaal** bericht met *belangrijke* gegevens.\n\n"
    "- Primair element\n"
    "- Secundair onderdeel\n"
    "- Tertiair component"
)


@pytest.mark.asyncio
async def test_nl_to_ru_feature_matrix_quality() -> None:
    """One live NL→RU call should cover markdown, clean output, target script, and latency."""
    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)

    start = time.perf_counter()
    result = await translator.translate(NL_TO_RU_MARKDOWN_TEXT)
    elapsed = time.perf_counter() - start

    assert result.strip(), "Translation should not be empty"
    assert_no_llm_chatter(result)
    assert result.startswith("#"), f"Heading formatting not preserved. Output: {result}"
    assert "**" in result, f"Bold markdown formatting not preserved. Output: {result}"
    assert "- " in result, f"List item formatting not preserved. Output: {result}"
    assert not re.search(r"[a-zA-Z]", result), f"Latin characters found in: {result}"
    assert elapsed < 5, f"Bidirectional translation took {elapsed:.2f}s — exceeds 5.00s performance threshold"


@pytest.mark.asyncio
async def test_non_source_language_translates_to_source() -> None:
    """Non-source language input (English) translates to configured source language (Dutch)."""
    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    result = await translator.translate("The quick brown fox jumps over the lazy dog.")

    assert result.strip(), "Translation should not be empty"
    assert_no_llm_chatter(result)
    # Should contain Dutch characteristics (no Cyrillic since output should be Dutch)
    assert not re.search(r"[а-яё]", result.lower()), f"Cyrillic characters found in Dutch output: {result}"
    # Should contain some Latin characters typical of Dutch
    assert re.search(r"[a-z]", result.lower()), f"No Latin characters found in Dutch output: {result}"


@pytest.mark.asyncio
async def test_constructor_order_affects_english_translation() -> None:
    """Same English input produces different outputs based on constructor order."""
    english_text = "Hello world! This is an important message."

    # Configuration 1: source=NL, target=RU -> English should translate to Dutch (source)
    translator_nl_source = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    result_to_dutch = await translator_nl_source.translate(english_text)

    # Configuration 2: source=RU, target=NL -> English should translate to Russian (source)
    translator_ru_source = BidirectionalTextTranslator(source_language=Language.RU, target_language=Language.NL)
    result_to_russian = await translator_ru_source.translate(english_text)

    # Both should be non-empty and clean
    assert result_to_dutch.strip(), "Dutch output should not be empty"
    assert result_to_russian.strip(), "Russian output should not be empty"
    assert_no_llm_chatter(result_to_dutch)
    assert_no_llm_chatter(result_to_russian)

    # Verify script characteristics
    assert not re.search(r"[\u0400-\u04FF]", result_to_dutch), f"Cyrillic found in Dutch output: {result_to_dutch}"
    assert re.search(r"[a-zA-Z]", result_to_dutch), f"No Latin in Dutch output: {result_to_dutch}"

    assert re.search(r"[\u0400-\u04FF]", result_to_russian), f"No Cyrillic in Russian output: {result_to_russian}"

    # Results should be different (proving constructor order has runtime effect)
    assert result_to_dutch != result_to_russian, (
        f"Constructor order should create different outputs.\n"
        f"source=NL output: {result_to_dutch}\n"
        f"source=RU output: {result_to_russian}"
    )
