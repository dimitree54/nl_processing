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
async def test_non_dutch_or_russian_text_returns_empty() -> None:
    """Input outside the configured pair should still return an empty string."""
    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    result = await translator.translate("The quick brown fox jumps over the lazy dog.")
    assert result == "", f"Expected empty string for non-Dutch/Russian input, got: '{result}'"
