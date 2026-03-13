"""POS-specific NL->RU detailed models for word extraction.

All models include Dutch lexical material plus Russian explanatory content
and shared learning fields.
"""

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

__all__ = [
    "NlRuNounDetails",
    "NlRuVerbDetails",
    "NlRuAdjectiveDetails",
    "NlRuAdverbDetails",
    "NlRuPrepositionDetails",
    "NlRuConjunctionDetails",
    "NlRuPronounDetails",
    "NlRuArticleDetails",
    "NlRuNumeralDetails",
    "NlRuInterjectionDetails",
    "NlRuProperNounPersonDetails",
    "NlRuProperNounCountryDetails",
    "NlRuPhraseDetails",
]
