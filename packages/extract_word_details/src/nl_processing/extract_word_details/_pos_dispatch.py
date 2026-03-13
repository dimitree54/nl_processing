"""POS dispatch logic for grouping words and managing supported POS types."""

from collections import defaultdict

from nl_processing.core.models import PartOfSpeech, Word
from nl_processing.extract_word_details.models._registry_init import SCHEMA_REGISTRY


def group_words_by_pos(words: list[Word]) -> dict[PartOfSpeech, list[tuple[int, Word]]]:
    """Group words by their POS, preserving original indices.

    Args:
        words: List of words to group

    Returns:
        Dictionary mapping POS to list of (original_index, word) tuples
    """
    groups: dict[PartOfSpeech, list[tuple[int, Word]]] = defaultdict(list)

    for index, word in enumerate(words):
        groups[word.word_type].append((index, word))

    return dict(groups)


def get_supported_pos() -> set[PartOfSpeech]:
    """Get the set of POS values that have registered models in the schema registry.

    Returns:
        Set of supported PartOfSpeech values
    """
    supported_pos = set()

    # Map schema keys to POS values based on the registry
    schema_to_pos = {
        "nl_ru_noun": PartOfSpeech.NOUN,
        "nl_ru_verb": PartOfSpeech.VERB,
        "nl_ru_adjective": PartOfSpeech.ADJECTIVE,
        "nl_ru_adverb": PartOfSpeech.ADVERB,
        "nl_ru_preposition": PartOfSpeech.PREPOSITION,
        "nl_ru_conjunction": PartOfSpeech.CONJUNCTION,
        "nl_ru_pronoun": PartOfSpeech.PRONOUN,
        "nl_ru_article": PartOfSpeech.ARTICLE,
        "nl_ru_numeral": PartOfSpeech.NUMERAL,
        "nl_ru_interjection": PartOfSpeech.INTERJECTION,
        "nl_ru_proper_noun_person": PartOfSpeech.PROPER_NOUN_PERSON,
        "nl_ru_proper_noun_country": PartOfSpeech.PROPER_NOUN_COUNTRY,
        "nl_ru_phrase": PartOfSpeech.PHRASE,
    }

    for schema_key in SCHEMA_REGISTRY.list_schemas():
        if schema_key in schema_to_pos:
            supported_pos.add(schema_to_pos[schema_key])

    return supported_pos


def split_supported_unsupported(
    words: list[Word], supported: set[PartOfSpeech]
) -> tuple[list[tuple[int, Word]], list[tuple[int, Word]]]:
    """Split words into supported and unsupported based on POS.

    Args:
        words: List of words to split
        supported: Set of supported POS values

    Returns:
        Tuple of (supported_words, unsupported_words) with original indices
    """
    supported_words = []
    unsupported_words = []

    for index, word in enumerate(words):
        if word.word_type in supported:
            supported_words.append((index, word))
        else:
            unsupported_words.append((index, word))

    return supported_words, unsupported_words
