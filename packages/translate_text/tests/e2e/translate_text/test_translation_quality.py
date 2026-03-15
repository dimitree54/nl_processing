import re
import time

from nl_processing.core.models import Language
import pytest

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

MARKDOWN_FEATURE_MATRIX_TEXT = (
    "# Belangrijke informatie\n\n"
    "Dit is een **belangrijk** bericht met *cursieve* tekst.\n\n"
    "- Eerste punt\n"
    "- Tweede punt\n"
    "- Derde punt"
)


def _assert_no_llm_chatter(result: str) -> None:
    for prefix in LLM_CHATTER_PREFIXES:
        assert not result.startswith(prefix), f"Output starts with LLM chatter prefix: '{prefix}'"


@pytest.mark.asyncio
async def test_markdown_feature_matrix_quality() -> None:
    """One live call should cover markdown, chatter-free output, Cyrillic output, and latency."""
    translator = TextTranslator(source_language=Language.NL, target_language=Language.RU)

    start = time.perf_counter()
    result = await translator.translate(MARKDOWN_FEATURE_MATRIX_TEXT)
    elapsed = time.perf_counter() - start

    assert result.strip(), "Translation should not be empty"
    _assert_no_llm_chatter(result)
    assert result.startswith("#"), f"Heading not preserved. Output: {result}"
    assert "**" in result, f"Bold markdown not preserved. Output: {result}"
    assert "- " in result, f"List items not preserved. Output: {result}"
    assert not re.search(r"[a-zA-Z]", result), f"Latin characters found in: {result}"
    assert elapsed < 5, f"Translation took {elapsed:.2f}s — exceeds 5.00s QA gate"


@pytest.mark.asyncio
async def test_non_dutch_text_returns_empty() -> None:
    """Non-Dutch text should still return an empty string."""
    translator = TextTranslator(source_language=Language.NL, target_language=Language.RU)
    result = await translator.translate("The quick brown fox jumps over the lazy dog.")
    assert result == "", f"Expected empty string for non-Dutch input, got: '{result}'"
