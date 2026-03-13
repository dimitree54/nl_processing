"""Batch wrapper models for POS-specific details extraction."""

from pydantic import BaseModel

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


class _NounDetailsBatch(BaseModel):
    """Batch wrapper for noun details."""

    details: list[NlRuNounDetails]


class _VerbDetailsBatch(BaseModel):
    """Batch wrapper for verb details."""

    details: list[NlRuVerbDetails]


class _AdjectiveDetailsBatch(BaseModel):
    """Batch wrapper for adjective details."""

    details: list[NlRuAdjectiveDetails]


class _AdverbDetailsBatch(BaseModel):
    """Batch wrapper for adverb details."""

    details: list[NlRuAdverbDetails]


class _PrepositionDetailsBatch(BaseModel):
    """Batch wrapper for preposition details."""

    details: list[NlRuPrepositionDetails]


class _ConjunctionDetailsBatch(BaseModel):
    """Batch wrapper for conjunction details."""

    details: list[NlRuConjunctionDetails]


class _PronounDetailsBatch(BaseModel):
    """Batch wrapper for pronoun details."""

    details: list[NlRuPronounDetails]


class _ArticleDetailsBatch(BaseModel):
    """Batch wrapper for article details."""

    details: list[NlRuArticleDetails]


class _NumeralDetailsBatch(BaseModel):
    """Batch wrapper for numeral details."""

    details: list[NlRuNumeralDetails]


class _InterjectionDetailsBatch(BaseModel):
    """Batch wrapper for interjection details."""

    details: list[NlRuInterjectionDetails]


class _ProperNounPersonDetailsBatch(BaseModel):
    """Batch wrapper for proper noun (person) details."""

    details: list[NlRuProperNounPersonDetails]


class _ProperNounCountryDetailsBatch(BaseModel):
    """Batch wrapper for proper noun (country) details."""

    details: list[NlRuProperNounCountryDetails]


class _PhraseDetailsBatch(BaseModel):
    """Batch wrapper for phrase details."""

    details: list[NlRuPhraseDetails]
