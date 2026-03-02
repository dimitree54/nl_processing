from enum import Enum

from pydantic import BaseModel


class Language(Enum):
    NL = "nl"
    RU = "ru"


class ExtractedText(BaseModel):
    text: str


class WordEntry(BaseModel):
    normalized_form: str
    word_type: str


class TranslationResult(BaseModel):
    translation: str
