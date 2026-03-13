"""Batch wrapper models for POS-specific details extraction."""

from pydantic import BaseModel

from nl_processing.extract_word_details.models import (
    NlRuAdjectiveDetails,
    NlRuAdverbDetails,
    NlRuArticleDetails,
    NlRuConjunctionDetails,
    NlRuInterjectionDetails,
    NlRuNounDetails,
    NlRuNumeralDetails,
    NlRuPhraseDetails,
    NlRuPrepositionDetails,
    NlRuPronounDetails,
    NlRuProperNounCountryDetails,
    NlRuProperNounPersonDetails,
    NlRuVerbDetails,
)


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
