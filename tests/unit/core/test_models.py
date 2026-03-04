from pydantic import ValidationError
import pytest

from nl_processing.core.models import ExtractedText, Language, PartOfSpeech, Word


def test_language_enum_values() -> None:
    """Test Language enum has correct values."""
    assert Language.NL.value == "nl"
    assert Language.RU.value == "ru"


def test_language_enum_count() -> None:
    """Test Language enum has exactly 2 members."""
    assert len(list(Language)) == 2


def test_language_enum_invalid_value() -> None:
    """Test Language enum rejects invalid values."""
    with pytest.raises(ValueError):
        Language("invalid")


def test_extracted_text_instantiation() -> None:
    """Test ExtractedText can be created and accessed."""
    extracted = ExtractedText(text="hello")
    assert extracted.text == "hello"


def test_extracted_text_serialization() -> None:
    """Test ExtractedText serialization via model_dump."""
    extracted = ExtractedText(text="hello")
    data = extracted.model_dump()
    assert data == {"text": "hello"}


def test_extracted_text_json_schema() -> None:
    """Test ExtractedText JSON schema contains text field."""
    schema = ExtractedText.model_json_schema()
    assert "text" in schema["properties"]
    assert schema["properties"]["text"]["type"] == "string"


def test_extracted_text_missing_field() -> None:
    """Test ExtractedText raises ValidationError on missing text field."""
    with pytest.raises(ValidationError):
        ExtractedText()


def test_part_of_speech_enum_values() -> None:
    """Test PartOfSpeech enum has correct values."""
    assert PartOfSpeech.NOUN.value == "noun"
    assert PartOfSpeech.VERB.value == "verb"
    assert PartOfSpeech.ADJECTIVE.value == "adjective"
    assert PartOfSpeech.ADVERB.value == "adverb"
    assert PartOfSpeech.PREPOSITION.value == "preposition"
    assert PartOfSpeech.CONJUNCTION.value == "conjunction"
    assert PartOfSpeech.PRONOUN.value == "pronoun"
    assert PartOfSpeech.ARTICLE.value == "article"
    assert PartOfSpeech.NUMERAL.value == "numeral"
    assert PartOfSpeech.PROPER_NOUN_PERSON.value == "proper_noun_person"
    assert PartOfSpeech.PROPER_NOUN_COUNTRY.value == "proper_noun_country"


def test_part_of_speech_enum_count() -> None:
    """Test PartOfSpeech enum has exactly 11 members."""
    assert len(list(PartOfSpeech)) == 11


def test_part_of_speech_enum_invalid_value() -> None:
    """Test PartOfSpeech enum rejects invalid values."""
    with pytest.raises(ValueError):
        PartOfSpeech("invalid")


def test_part_of_speech_from_string() -> None:
    """Test PartOfSpeech can be created from string value."""
    assert PartOfSpeech("noun") == PartOfSpeech.NOUN
    assert PartOfSpeech("proper_noun_person") == PartOfSpeech.PROPER_NOUN_PERSON


def test_word_instantiation() -> None:
    """Test Word can be created and accessed."""
    word = Word(normalized_form="de fiets", word_type=PartOfSpeech.NOUN, language=Language.NL)
    assert word.normalized_form == "de fiets"
    assert word.word_type == PartOfSpeech.NOUN
    assert word.language == Language.NL


def test_word_with_string_word_type() -> None:
    """Test Word accepts string value for word_type (Pydantic coercion)."""
    word = Word(normalized_form="lopen", word_type="verb", language=Language.NL)
    assert word.word_type == PartOfSpeech.VERB


def test_word_serialization() -> None:
    """Test Word serialization via model_dump (mode='json' for string enum values)."""
    word = Word(normalized_form="de kat", word_type=PartOfSpeech.NOUN, language=Language.NL)
    data = word.model_dump(mode="json")
    assert data == {"normalized_form": "de kat", "word_type": "noun", "language": "nl"}


def test_word_missing_fields() -> None:
    """Test Word raises ValidationError on missing fields."""
    with pytest.raises(ValidationError):
        Word(normalized_form="de fiets", word_type=PartOfSpeech.NOUN)

    with pytest.raises(ValidationError):
        Word(normalized_form="de fiets", language=Language.NL)

    with pytest.raises(ValidationError):
        Word(word_type=PartOfSpeech.NOUN, language=Language.NL)

    with pytest.raises(ValidationError):
        Word()


def test_word_invalid_word_type() -> None:
    """Test Word rejects invalid word_type values."""
    with pytest.raises(ValidationError):
        Word(normalized_form="test", word_type="invalid_type", language=Language.NL)


def test_word_russian_language() -> None:
    """Test Word with Russian language (for translate_word output)."""
    word = Word(normalized_form="дом", word_type=PartOfSpeech.NOUN, language=Language.RU)
    assert word.normalized_form == "дом"
    assert word.word_type == PartOfSpeech.NOUN
    assert word.language == Language.RU


def test_all_models_accept_empty_strings() -> None:
    """Test all models accept empty strings (per architecture)."""
    extracted = ExtractedText(text="")
    word = Word(normalized_form="", word_type=PartOfSpeech.NOUN, language=Language.NL)

    assert extracted.text == ""
    assert word.normalized_form == ""
