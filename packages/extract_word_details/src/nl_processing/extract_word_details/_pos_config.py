"""POS configuration mapping for extraction chains."""

from nl_processing.core.models import PartOfSpeech

from nl_processing.extract_word_details._batch_models import (
    _AdjectiveDetailsBatch,
    _AdverbDetailsBatch,
    _ArticleDetailsBatch,
    _ConjunctionDetailsBatch,
    _InterjectionDetailsBatch,
    _NounDetailsBatch,
    _NumeralDetailsBatch,
    _PhraseDetailsBatch,
    _PrepositionDetailsBatch,
    _PronounDetailsBatch,
    _ProperNounCountryDetailsBatch,
    _ProperNounPersonDetailsBatch,
    _VerbDetailsBatch,
)

# Mapping from POS to batch wrapper and schema info
POS_CONFIG = {
    PartOfSpeech.NOUN: {
        "batch_model": _NounDetailsBatch,
        "prompt_file": "nl_ru_noun.json",
        "schema_key": "nl_ru_noun",
        "schema_version": 1,
    },
    PartOfSpeech.VERB: {
        "batch_model": _VerbDetailsBatch,
        "prompt_file": "nl_ru_verb.json",
        "schema_key": "nl_ru_verb",
        "schema_version": 1,
    },
    PartOfSpeech.ADJECTIVE: {
        "batch_model": _AdjectiveDetailsBatch,
        "prompt_file": "nl_ru_adjective.json",
        "schema_key": "nl_ru_adjective",
        "schema_version": 1,
    },
    PartOfSpeech.ADVERB: {
        "batch_model": _AdverbDetailsBatch,
        "prompt_file": "nl_ru_adverb.json",
        "schema_key": "nl_ru_adverb",
        "schema_version": 1,
    },
    PartOfSpeech.PREPOSITION: {
        "batch_model": _PrepositionDetailsBatch,
        "prompt_file": "nl_ru_preposition.json",
        "schema_key": "nl_ru_preposition",
        "schema_version": 1,
    },
    PartOfSpeech.CONJUNCTION: {
        "batch_model": _ConjunctionDetailsBatch,
        "prompt_file": "nl_ru_conjunction.json",
        "schema_key": "nl_ru_conjunction",
        "schema_version": 1,
    },
    PartOfSpeech.PRONOUN: {
        "batch_model": _PronounDetailsBatch,
        "prompt_file": "nl_ru_pronoun.json",
        "schema_key": "nl_ru_pronoun",
        "schema_version": 1,
    },
    PartOfSpeech.ARTICLE: {
        "batch_model": _ArticleDetailsBatch,
        "prompt_file": "nl_ru_article.json",
        "schema_key": "nl_ru_article",
        "schema_version": 1,
    },
    PartOfSpeech.NUMERAL: {
        "batch_model": _NumeralDetailsBatch,
        "prompt_file": "nl_ru_numeral.json",
        "schema_key": "nl_ru_numeral",
        "schema_version": 1,
    },
    PartOfSpeech.INTERJECTION: {
        "batch_model": _InterjectionDetailsBatch,
        "prompt_file": "nl_ru_interjection.json",
        "schema_key": "nl_ru_interjection",
        "schema_version": 1,
    },
    PartOfSpeech.PROPER_NOUN_PERSON: {
        "batch_model": _ProperNounPersonDetailsBatch,
        "prompt_file": "nl_ru_proper_noun_person.json",
        "schema_key": "nl_ru_proper_noun_person",
        "schema_version": 1,
    },
    PartOfSpeech.PROPER_NOUN_COUNTRY: {
        "batch_model": _ProperNounCountryDetailsBatch,
        "prompt_file": "nl_ru_proper_noun_country.json",
        "schema_key": "nl_ru_proper_noun_country",
        "schema_version": 1,
    },
    PartOfSpeech.PHRASE: {
        "batch_model": _PhraseDetailsBatch,
        "prompt_file": "nl_ru_phrase.json",
        "schema_key": "nl_ru_phrase",
        "schema_version": 1,
    },
}
