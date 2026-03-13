"""Schema registry initialization for all POS-specific models.

Creates and registers all 13 POS models in the global SCHEMA_REGISTRY.
"""

from nl_processing.extract_word_details._schema_registry import SchemaRegistry
from nl_processing.extract_word_details.models._adjective import NlRuAdjectiveDetails
from nl_processing.extract_word_details.models._adverb import NlRuAdverbDetails
from nl_processing.extract_word_details.models._article import NlRuArticleDetails
from nl_processing.extract_word_details.models._conjunction import NlRuConjunctionDetails
from nl_processing.extract_word_details.models._interjection import NlRuInterjectionDetails
from nl_processing.extract_word_details.models._noun import NlRuNounDetails
from nl_processing.extract_word_details.models._numeral import NlRuNumeralDetails
from nl_processing.extract_word_details.models._phrase import NlRuPhraseDetails
from nl_processing.extract_word_details.models._preposition import NlRuPrepositionDetails
from nl_processing.extract_word_details.models._pronoun import NlRuPronounDetails
from nl_processing.extract_word_details.models._proper_noun import (
    NlRuProperNounCountryDetails,
    NlRuProperNounPersonDetails,
)
from nl_processing.extract_word_details.models._verb import NlRuVerbDetails

# Global schema registry instance
SCHEMA_REGISTRY = SchemaRegistry()

# Register all 13 POS models with nl_ru_{pos_value} pattern and version 1
SCHEMA_REGISTRY.register("nl_ru_noun", 1, NlRuNounDetails)
SCHEMA_REGISTRY.register("nl_ru_verb", 1, NlRuVerbDetails)
SCHEMA_REGISTRY.register("nl_ru_adjective", 1, NlRuAdjectiveDetails)
SCHEMA_REGISTRY.register("nl_ru_adverb", 1, NlRuAdverbDetails)
SCHEMA_REGISTRY.register("nl_ru_preposition", 1, NlRuPrepositionDetails)
SCHEMA_REGISTRY.register("nl_ru_conjunction", 1, NlRuConjunctionDetails)
SCHEMA_REGISTRY.register("nl_ru_pronoun", 1, NlRuPronounDetails)
SCHEMA_REGISTRY.register("nl_ru_article", 1, NlRuArticleDetails)
SCHEMA_REGISTRY.register("nl_ru_numeral", 1, NlRuNumeralDetails)
SCHEMA_REGISTRY.register("nl_ru_interjection", 1, NlRuInterjectionDetails)
SCHEMA_REGISTRY.register("nl_ru_proper_noun_person", 1, NlRuProperNounPersonDetails)
SCHEMA_REGISTRY.register("nl_ru_proper_noun_country", 1, NlRuProperNounCountryDetails)
SCHEMA_REGISTRY.register("nl_ru_phrase", 1, NlRuPhraseDetails)
