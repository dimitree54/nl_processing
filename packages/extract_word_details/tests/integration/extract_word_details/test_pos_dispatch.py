"""Unit tests for POS dispatch helper functions."""

from nl_processing.core.models import Language, PartOfSpeech, Word

from nl_processing.extract_word_details._pos_dispatch import (
    get_supported_pos,
    group_words_by_pos,
    split_supported_unsupported,
)


class TestGroupWordsByPos:
    """Test word grouping by part of speech."""

    def test_groups_words_correctly(self) -> None:
        """Test that words are grouped correctly by POS."""
        words = [
            Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL),
            Word(normalized_form="lopen", word_type=PartOfSpeech.VERB, language=Language.NL),
            Word(normalized_form="kat", word_type=PartOfSpeech.NOUN, language=Language.NL),
        ]
        result = group_words_by_pos(words)

        assert PartOfSpeech.NOUN in result
        assert PartOfSpeech.VERB in result
        assert len(result[PartOfSpeech.NOUN]) == 2
        assert len(result[PartOfSpeech.VERB]) == 1

    def test_preserves_original_indices(self) -> None:
        """Test that original word indices are preserved in grouping."""
        words = [
            Word(normalized_form="groot", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL),
            Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL),
            Word(normalized_form="snel", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL),
        ]
        result = group_words_by_pos(words)

        # Check that indices are preserved
        adjectives = result[PartOfSpeech.ADJECTIVE]
        assert adjectives[0] == (0, words[0])  # "groot" at index 0
        assert adjectives[1] == (2, words[2])  # "snel" at index 2

        nouns = result[PartOfSpeech.NOUN]
        assert nouns[0] == (1, words[1])  # "hond" at index 1

    def test_handles_empty_list(self) -> None:
        """Test that empty word list returns empty dict."""
        result = group_words_by_pos([])
        assert result == {}

    def test_handles_single_word(self) -> None:
        """Test that single word is handled correctly."""
        words = [Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL)]
        result = group_words_by_pos(words)

        assert len(result) == 1
        assert PartOfSpeech.NOUN in result
        assert result[PartOfSpeech.NOUN] == [(0, words[0])]


class TestGetSupportedPos:
    """Test supported POS retrieval."""

    def test_returns_all_13_pos(self) -> None:
        """Test that all 13 supported POS values are returned."""
        supported = get_supported_pos()
        assert len(supported) == 13

    def test_returns_expected_pos_types(self) -> None:
        """Test that expected POS types are included in supported set."""
        supported = get_supported_pos()

        # Check for some key POS types that should be supported
        expected_pos = {
            PartOfSpeech.NOUN,
            PartOfSpeech.VERB,
            PartOfSpeech.ADJECTIVE,
            PartOfSpeech.ADVERB,
            PartOfSpeech.PREPOSITION,
            PartOfSpeech.CONJUNCTION,
            PartOfSpeech.PRONOUN,
            PartOfSpeech.ARTICLE,
            PartOfSpeech.NUMERAL,
            PartOfSpeech.INTERJECTION,
            PartOfSpeech.PROPER_NOUN_PERSON,
            PartOfSpeech.PROPER_NOUN_COUNTRY,
            PartOfSpeech.PHRASE,
        }

        assert expected_pos.issubset(supported)

    def test_returns_set_type(self) -> None:
        """Test that returned value is a set."""
        supported = get_supported_pos()
        assert isinstance(supported, set)


class TestSplitSupportedUnsupported:
    """Test splitting words into supported and unsupported categories."""

    def test_splits_correctly_with_supported_pos(self) -> None:
        """Test that words with supported POS are categorized correctly."""
        words = [
            Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL),
            Word(normalized_form="lopen", word_type=PartOfSpeech.VERB, language=Language.NL),
        ]
        supported_pos = {PartOfSpeech.NOUN, PartOfSpeech.VERB}

        supported_words, unsupported_words = split_supported_unsupported(words, supported_pos)

        assert len(supported_words) == 2
        assert len(unsupported_words) == 0
        assert supported_words == [(0, words[0]), (1, words[1])]

    def test_splits_correctly_with_unsupported_pos(self) -> None:
        """Test that words with unsupported POS are categorized correctly."""
        words = [
            Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL),
            Word(normalized_form="unknown", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL),
        ]
        supported_pos = {PartOfSpeech.NOUN}  # Only NOUN is supported

        supported_words, unsupported_words = split_supported_unsupported(words, supported_pos)

        assert len(supported_words) == 1
        assert len(unsupported_words) == 1
        assert supported_words == [(0, words[0])]
        assert unsupported_words == [(1, words[1])]

    def test_splits_correctly_mixed_pos(self) -> None:
        """Test mixed supported and unsupported POS categorization."""
        words = [
            Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL),
            Word(normalized_form="unknown", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL),
            Word(normalized_form="lopen", word_type=PartOfSpeech.VERB, language=Language.NL),
            Word(normalized_form="another", word_type=PartOfSpeech.ADVERB, language=Language.NL),
        ]
        supported_pos = {PartOfSpeech.NOUN, PartOfSpeech.VERB}  # Only NOUN and VERB supported

        supported_words, unsupported_words = split_supported_unsupported(words, supported_pos)

        assert len(supported_words) == 2
        assert len(unsupported_words) == 2
        assert supported_words == [(0, words[0]), (2, words[2])]
        assert unsupported_words == [(1, words[1]), (3, words[3])]

    def test_handles_empty_word_list(self) -> None:
        """Test that empty word list returns empty tuples."""
        supported_pos = {PartOfSpeech.NOUN}

        supported_words, unsupported_words = split_supported_unsupported([], supported_pos)

        assert supported_words == []
        assert unsupported_words == []

    def test_handles_empty_supported_set(self) -> None:
        """Test that empty supported set categorizes all as unsupported."""
        words = [
            Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL),
            Word(normalized_form="lopen", word_type=PartOfSpeech.VERB, language=Language.NL),
        ]
        supported_pos = set()  # No POS supported

        supported_words, unsupported_words = split_supported_unsupported(words, supported_pos)

        assert len(supported_words) == 0
        assert len(unsupported_words) == 2
        assert unsupported_words == [(0, words[0]), (1, words[1])]
