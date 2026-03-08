from nl_processing.core.models import PartOfSpeech, Word
import pytest

from nl_processing.extract_words_from_text.service import WordExtractor


@pytest.mark.asyncio
async def test_markdown_formatted_dutch_text() -> None:
    """E2e: markdown formatting is ignored, only linguistic content extracted."""
    text = "# Welkom\n\nDit is een **belangrijke** tekst.\n\n- De kat\n- Het huis"

    extractor = WordExtractor()
    result = await extractor.extract(text)

    assert len(result) > 0, "Expected non-empty result for Dutch markdown text"
    assert all(isinstance(w, Word) for w in result)

    for w in result:
        assert "#" not in w.normalized_form, f"Markdown heading symbol found: {w.normalized_form}"
        assert "**" not in w.normalized_form, f"Markdown bold symbol found: {w.normalized_form}"


@pytest.mark.asyncio
async def test_full_pipeline_various_word_types() -> None:
    """E2e: longer Dutch text with various word types produces valid Word objects."""
    text = (
        "De oude man wandelt langzaam door het mooie park. "
        "Zijn hond rent vrolijk achter de eenden aan. "
        "Maria kijkt naar de zonsondergang boven Amsterdam."
    )

    extractor = WordExtractor()
    result = await extractor.extract(text)

    assert len(result) > 5, f"Expected many words, got {len(result)}"
    assert all(isinstance(w, Word) for w in result)

    for w in result:
        assert w.normalized_form, "normalized_form must not be empty"
        assert isinstance(w.word_type, PartOfSpeech), "word_type must be PartOfSpeech"


@pytest.mark.asyncio
async def test_non_dutch_text_returns_empty_list() -> None:
    """E2e: non-Dutch text returns empty list."""
    text = "Привет, как дела? Сегодня хорошая погода."

    extractor = WordExtractor()
    result = await extractor.extract(text)

    assert result == [], f"Expected empty list for Russian text, got {len(result)} items"


@pytest.mark.asyncio
async def test_mixed_markdown_with_compound_expressions() -> None:
    """E2e: markdown text with compound expressions extracts valid entries."""
    text = "## Les 3: Uitdrukkingen\n\nHij komt **er achter** dat het moeilijk is.\nZij houdt *rekening* met de kosten."

    extractor = WordExtractor()
    result = await extractor.extract(text)

    assert len(result) > 0, "Expected non-empty result for Dutch text with expressions"
    assert all(isinstance(w, Word) for w in result)

    for w in result:
        assert w.normalized_form, "normalized_form must not be empty"
        assert isinstance(w.word_type, PartOfSpeech), "word_type must be PartOfSpeech"


@pytest.mark.asyncio
async def test_all_results_have_valid_fields() -> None:
    """E2e: every returned Word has non-empty normalized_form and valid word_type."""
    text = "Nederland is een prachtig land met veel water en fietspaden."

    extractor = WordExtractor()
    result = await extractor.extract(text)

    assert len(result) > 0, "Expected non-empty result"

    for w in result:
        assert isinstance(w, Word), f"Expected Word, got {type(w)}"
        assert isinstance(w.normalized_form, str), "normalized_form must be str"
        assert isinstance(w.word_type, PartOfSpeech), "word_type must be PartOfSpeech"
        assert len(w.normalized_form) > 0, "normalized_form must not be empty"
