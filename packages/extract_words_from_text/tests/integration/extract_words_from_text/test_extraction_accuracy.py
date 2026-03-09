import time

from nl_processing.core.models import Word
import pytest

from nl_processing.extract_words_from_text.service import WordExtractor


async def _assert_extraction(text: str, expected: set[tuple[str, str]]) -> None:
    """Extract words from text and assert exact set match against expected."""
    extractor = WordExtractor()
    result = await extractor.extract(text)
    actual = {(w.normalized_form, w.word_type.value) for w in result}
    assert actual == expected, f"Mismatch.\nExpected: {expected}\nGot: {actual}"


@pytest.mark.asyncio
async def test_nouns_and_verbs() -> None:
    """Test extraction of nouns (de/het), verbs, adjective, preposition."""
    await _assert_extraction(
        "De grote kat loopt door de tuin.",
        {
            ("de kat", "noun"),
            ("groot", "adjective"),
            ("lopen", "verb"),
            ("de tuin", "noun"),
            ("door", "preposition"),
        },
    )


@pytest.mark.asyncio
async def test_proper_nouns_and_prepositions() -> None:
    """Test extraction of proper nouns (person, country) and prepositions."""
    await _assert_extraction(
        "Jan woont in Nederland.",
        {
            ("Jan", "proper_noun_person"),
            ("wonen", "verb"),
            ("in", "preposition"),
            ("Nederland", "proper_noun_country"),
        },
    )


@pytest.mark.asyncio
async def test_articles_and_adjectives() -> None:
    """Test extraction with de/het articles and multiple adjectives."""
    await _assert_extraction(
        "Het kleine kind speelt met de rode bal.",
        {
            ("het kind", "noun"),
            ("klein", "adjective"),
            ("spelen", "verb"),
            ("met", "preposition"),
            ("de bal", "noun"),
            ("rood", "adjective"),
        },
    )


@pytest.mark.asyncio
async def test_compound_expression() -> None:
    """Test extraction of compound verbal expression."""
    await _assert_extraction(
        "Zij gaat er vandoor met haar vriend.",
        {
            ("zij", "pronoun"),
            ("ervandoor gaan", "verb"),
            ("met", "preposition"),
            ("haar", "pronoun"),
            ("de vriend", "noun"),
        },
    )


@pytest.mark.asyncio
async def test_non_dutch_returns_empty() -> None:
    """Test that non-Dutch text returns an empty list."""
    text = "The quick brown fox jumps over the lazy dog."

    extractor = WordExtractor()
    result = await extractor.extract(text)

    assert result == [], f"Expected empty list for English text, got: {result}"


@pytest.mark.asyncio
async def test_performance_100_words() -> None:
    """Test that extraction of ~100 words completes in <5 seconds."""
    text = (
        "Nederland is een prachtig land in West-Europa. "
        "Het land staat bekend om zijn tulpen, molens en kaas. "
        "De hoofdstad Amsterdam trekt elk jaar miljoenen toeristen. "
        "Veel mensen fietsen dagelijks naar hun werk of school. "
        "De Nederlandse keuken is gevarieerd en smakelijk. "
        "Stamppot is een traditioneel gerecht dat veel Nederlanders graag eten. "
        "Het weer in Nederland is wisselvallig, met veel regen en wind. "
        "Ondanks het koude klimaat zijn de Nederlanders een vrolijk volk. "
        "Ze houden van gezelligheid en brengen graag tijd door met familie. "
        "De Nederlandse taal is nauw verwant aan het Duits en het Engels. "
        "Veel Nederlanders spreken vloeiend meerdere talen."
    )

    extractor = WordExtractor()
    start = time.time()
    result = await extractor.extract(text)
    elapsed = time.time() - start

    assert elapsed < 180, f"Extraction took {elapsed:.2f}s -- exceeds 180.00s QA gate"
    assert len(result) > 0, "Expected non-empty result for Dutch text"
    assert all(isinstance(w, Word) for w in result)
