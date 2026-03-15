import re
import time

from nl_processing.core.models import Language
import pytest

from nl_processing.translate_text_bidirectional.service import BidirectionalTextTranslator
from tests.e2e.translate_text_bidirectional.assertions import assert_no_llm_chatter

RU_TO_NL_MARKDOWN_TEXT = (
    "# Важная информация\n\n"
    "Это **важное** сообщение с *курсивным* текстом.\n\n"
    "- Первый пункт\n"
    "- Второй пункт\n"
    "- Третий пункт"
)


@pytest.mark.asyncio
async def test_ru_to_nl_feature_matrix_quality() -> None:
    """One live RU→NL call should cover markdown, clean output, target script, and latency."""
    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)

    start = time.perf_counter()
    result = await translator.translate(RU_TO_NL_MARKDOWN_TEXT)
    elapsed = time.perf_counter() - start

    assert result.strip(), "Translation should not be empty"
    assert_no_llm_chatter(result)
    assert result.startswith("#"), f"Heading not preserved. Output: {result}"
    assert "**" in result, f"Bold markdown not preserved. Output: {result}"
    assert "- " in result, f"List items not preserved. Output: {result}"
    assert not re.search(r"[\u0400-\u04FF]", result), f"Cyrillic characters found in: {result}"
    assert elapsed < 5, f"Translation took {elapsed:.2f}s — exceeds 5.00s QA gate"


@pytest.mark.asyncio
async def test_ru_source_configuration_live_behavior() -> None:
    """Live test with source=RU,target=NL proves constructor order affects runtime behavior."""
    # For source=RU,target=NL: Russian input->Dutch output, Dutch input->Russian output
    translator = BidirectionalTextTranslator(source_language=Language.RU, target_language=Language.NL)

    # Test 1: Russian (source) input -> Dutch (target) output
    start = time.perf_counter()
    result_ru_to_nl = await translator.translate("Привет, мир! Это **важное** сообщение.")
    elapsed_ru = time.perf_counter() - start

    assert result_ru_to_nl.strip(), "Russian->Dutch translation should not be empty"
    assert_no_llm_chatter(result_ru_to_nl)
    assert "**" in result_ru_to_nl, f"Bold markdown not preserved in RU->NL. Output: {result_ru_to_nl}"
    assert not re.search(r"[\u0400-\u04FF]", result_ru_to_nl), f"Cyrillic in Dutch output: {result_ru_to_nl}"
    assert re.search(r"[a-zA-Z]", result_ru_to_nl), f"No Latin characters in Dutch output: {result_ru_to_nl}"
    assert elapsed_ru < 5, f"RU->NL translation took {elapsed_ru:.2f}s — exceeds 5.00s gate"

    # Test 2: Dutch (non-source) input -> Russian (source) output
    start = time.perf_counter()
    result_nl_to_ru = await translator.translate("Hallo wereld! Dit is een **belangrijk** bericht.")
    elapsed_nl = time.perf_counter() - start

    assert result_nl_to_ru.strip(), "Dutch->Russian translation should not be empty"
    assert_no_llm_chatter(result_nl_to_ru)
    assert "**" in result_nl_to_ru, f"Bold markdown not preserved in NL->RU. Output: {result_nl_to_ru}"
    assert re.search(r"[\u0400-\u04FF]", result_nl_to_ru), f"No Cyrillic in Russian output: {result_nl_to_ru}"
    assert elapsed_nl < 5, f"NL->RU translation took {elapsed_nl:.2f}s — exceeds 5.00s gate"
