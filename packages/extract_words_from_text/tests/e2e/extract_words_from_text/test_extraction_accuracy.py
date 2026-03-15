import time

from nl_processing.core.models import Language
import pytest

from nl_processing.extract_words_from_text.service import WordExtractor
from tests.e2e.extract_words_from_text.assertions import (
    assert_words_match_contract,
    format_diff,
    word_pairs,
)

FEATURE_MATRIX_TEXT = (
    "- De **grote** kat loopt door de tuin.\n"
    "- Jan woont in Nederland.\n"
    "- Het kleine kind speelt met de *rode* bal.\n"
    "- Zij gaat er vandoor met haar vriend."
)

FEATURE_MATRIX_EXPECTED: set[tuple[str, str]] = {
    ("de kat", "noun"),
    ("groot", "adjective"),
    ("lopen", "verb"),
    ("de tuin", "noun"),
    ("door", "preposition"),
    ("Jan", "proper_noun_person"),
    ("wonen", "verb"),
    ("in", "preposition"),
    ("Nederland", "proper_noun_country"),
    ("het kind", "noun"),
    ("klein", "adjective"),
    ("spelen", "verb"),
    ("met", "preposition"),
    ("de bal", "noun"),
    ("rood", "adjective"),
    ("zij", "pronoun"),
    ("ervandoor gaan", "verb"),
    ("haar", "pronoun"),
    ("de vriend", "noun"),
}


@pytest.mark.asyncio
async def test_markdown_feature_matrix_quality() -> None:
    """E2e quality: one extraction call validates the main Dutch text features."""
    extractor = WordExtractor()

    start = time.perf_counter()
    result = await extractor.extract(FEATURE_MATRIX_TEXT)
    elapsed = time.perf_counter() - start

    assert elapsed < 180, f"Extraction took {elapsed:.2f}s -- exceeds 180.00s QA gate"
    assert_words_match_contract(result, language=Language.NL)
    assert all("#" not in word.normalized_form for word in result)
    assert all("*" not in word.normalized_form for word in result)

    actual = word_pairs(result)
    assert actual == FEATURE_MATRIX_EXPECTED, (
        f"Feature-matrix extraction mismatch:\n{format_diff(FEATURE_MATRIX_EXPECTED, actual)}"
    )


@pytest.mark.asyncio
async def test_non_dutch_returns_empty() -> None:
    """E2e quality: non-target-language text returns an empty list."""
    extractor = WordExtractor()
    result = await extractor.extract("The quick brown fox jumps over the lazy dog.")
    assert result == [], f"Expected empty list for English text, got: {result}"
