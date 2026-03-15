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
