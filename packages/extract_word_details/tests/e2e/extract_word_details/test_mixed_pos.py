"""End-to-end tests for mixed POS word extraction scenarios."""

from nl_processing.core.models import Language, PartOfSpeech, Word
import pytest

from nl_processing.extract_word_details.service import WordDetailsExtractor


@pytest.fixture
def extractor() -> WordDetailsExtractor:
    return WordDetailsExtractor(
        source_language=Language.NL,
        target_language=Language.RU,
    )


@pytest.mark.asyncio
async def test_mixed_pos_extraction(extractor: WordDetailsExtractor) -> None:
    """Test end-to-end extraction for words with different POS types."""
    words = [
        Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="lopen", word_type=PartOfSpeech.VERB, language=Language.NL),
        Word(normalized_form="groot", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL),
        Word(normalized_form="snel", word_type=PartOfSpeech.ADVERB, language=Language.NL),
    ]

    results = await extractor.extract(words)

    assert len(results) == 4

    # Verify each word got processed with correct schema
    noun_result = results[0]
    assert noun_result.source_word == "hond"
    assert noun_result.word_type == "noun"
    assert noun_result.schema_key == "nl_ru_noun"

    verb_result = results[1]
    assert verb_result.source_word == "lopen"
    assert verb_result.word_type == "verb"
    assert verb_result.schema_key == "nl_ru_verb"

    adj_result = results[2]
    assert adj_result.source_word == "groot"
    assert adj_result.word_type == "adjective"
    assert adj_result.schema_key == "nl_ru_adjective"

    adv_result = results[3]
    assert adv_result.source_word == "snel"
    assert adv_result.word_type == "adverb"
    assert adv_result.schema_key == "nl_ru_adverb"


@pytest.mark.asyncio
async def test_comprehensive_pos_extraction(extractor: WordDetailsExtractor) -> None:
    """Test extraction for as many POS types as possible."""
    words = [
        Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="lopen", word_type=PartOfSpeech.VERB, language=Language.NL),
        Word(normalized_form="groot", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL),
        Word(normalized_form="snel", word_type=PartOfSpeech.ADVERB, language=Language.NL),
        Word(normalized_form="van", word_type=PartOfSpeech.PREPOSITION, language=Language.NL),
        Word(normalized_form="en", word_type=PartOfSpeech.CONJUNCTION, language=Language.NL),
        Word(normalized_form="ik", word_type=PartOfSpeech.PRONOUN, language=Language.NL),
        Word(normalized_form="de", word_type=PartOfSpeech.ARTICLE, language=Language.NL),
    ]

    results = await extractor.extract(words)

    # All words should be supported and extracted
    assert len(results) == 8

    # Verify schema keys are different for different POS
    schema_keys = [result.schema_key for result in results]
    assert "nl_ru_noun" in schema_keys
    assert "nl_ru_verb" in schema_keys
    assert "nl_ru_adjective" in schema_keys
    assert "nl_ru_adverb" in schema_keys
    assert "nl_ru_preposition" in schema_keys
    assert "nl_ru_conjunction" in schema_keys
    assert "nl_ru_pronoun" in schema_keys
    assert "nl_ru_article" in schema_keys


@pytest.mark.asyncio
async def test_batch_processing_efficiency(extractor: WordDetailsExtractor) -> None:
    """Test that multiple words of same POS are processed efficiently in batches."""
    # Create multiple nouns for batch processing
    words = [
        Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="kat", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="vogel", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="vis", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="boom", word_type=PartOfSpeech.NOUN, language=Language.NL),
    ]

    results = await extractor.extract(words)

    assert len(results) == 5
    assert all(result.word_type == "noun" for result in results)
    assert all(result.schema_key == "nl_ru_noun" for result in results)

    # Verify order preservation in batch processing
    expected_words = ["hond", "kat", "vogel", "vis", "boom"]
    actual_words = [result.source_word for result in results]
    assert actual_words == expected_words


@pytest.mark.asyncio
async def test_complex_mixed_order_preservation(extractor: WordDetailsExtractor) -> None:
    """Test order preservation in complex mixed POS scenarios."""
    # Create a complex mixed pattern: adj, noun, adverb, verb, adj, noun
    words = [
        Word(normalized_form="groot", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL),
        Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="snel", word_type=PartOfSpeech.ADVERB, language=Language.NL),
        Word(normalized_form="lopen", word_type=PartOfSpeech.VERB, language=Language.NL),
        Word(normalized_form="klein", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL),
        Word(normalized_form="kat", word_type=PartOfSpeech.NOUN, language=Language.NL),
    ]

    results = await extractor.extract(words)

    assert len(results) == 6

    # Verify exact order preservation
    assert results[0].source_word == "groot" and results[0].word_type == "adjective"
    assert results[1].source_word == "hond" and results[1].word_type == "noun"
    assert results[2].source_word == "snel" and results[2].word_type == "adverb"
    assert results[3].source_word == "lopen" and results[3].word_type == "verb"
    assert results[4].source_word == "klein" and results[4].word_type == "adjective"
    assert results[5].source_word == "kat" and results[5].word_type == "noun"


@pytest.mark.asyncio
async def test_single_word_per_pos(extractor: WordDetailsExtractor) -> None:
    """Test edge case of single word per POS type."""
    # Single word of each type to test individual chain calls
    words = [
        Word(normalized_form="water", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="zwemmen", word_type=PartOfSpeech.VERB, language=Language.NL),
        Word(normalized_form="nat", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL),
    ]

    results = await extractor.extract(words)

    assert len(results) == 3
    assert results[0].source_word == "water"
    assert results[1].source_word == "zwemmen"
    assert results[2].source_word == "nat"


@pytest.mark.asyncio
async def test_payload_structure_completeness(extractor: WordDetailsExtractor) -> None:
    """Test that extracted payloads have expected structure and completeness."""
    words = [
        Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="lopen", word_type=PartOfSpeech.VERB, language=Language.NL),
    ]

    results = await extractor.extract(words)

    assert len(results) == 2

    # Verify payload structure exists and is non-empty
    for result in results:
        assert isinstance(result.payload, dict)
        assert len(result.payload) > 0
        assert result.schema_version == 1

        # Verify basic database record structure
        assert result.source_word is not None
        assert result.word_type is not None
        assert result.schema_key is not None
