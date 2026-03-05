from enum import Enum

from pydantic import BaseModel


class Language(Enum):
    NL = "nl"
    RU = "ru"


class PartOfSpeech(Enum):
    """Part of speech classification for extracted and translated words.

    This enum is extensible -- additional values can be added for
    language-specific grammatical categories (e.g., proper_noun_city,
    particle) without breaking existing code that doesn't use them.
    """

    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    PREPOSITION = "preposition"
    CONJUNCTION = "conjunction"
    PRONOUN = "pronoun"
    ARTICLE = "article"
    NUMERAL = "numeral"
    INTERJECTION = "interjection"
    PROPER_NOUN_PERSON = "proper_noun_person"
    PROPER_NOUN_COUNTRY = "proper_noun_country"


class ExtractedText(BaseModel):
    text: str


class Word(BaseModel):
    """Unified word model for extracted and translated words.

    Used as the public return type for both extract_words_from_text
    and translate_word modules. The language field is set
    programmatically by the service, not by the LLM.
    """

    normalized_form: str
    word_type: PartOfSpeech
    language: Language
