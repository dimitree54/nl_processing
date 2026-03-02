from pydantic import ValidationError
import pytest

from nl_processing.core.models import ExtractedText, Language, TranslationResult, WordEntry


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


def test_word_entry_instantiation() -> None:
    """Test WordEntry can be created and accessed."""
    word = WordEntry(normalized_form="de fiets", word_type="noun")
    assert word.normalized_form == "de fiets"
    assert word.word_type == "noun"


def test_word_entry_missing_fields() -> None:
    """Test WordEntry raises ValidationError on missing fields."""
    with pytest.raises(ValidationError):
        WordEntry(normalized_form="de fiets")

    with pytest.raises(ValidationError):
        WordEntry(word_type="noun")

    with pytest.raises(ValidationError):
        WordEntry()


def test_translation_result_instantiation() -> None:
    """Test TranslationResult can be created and accessed."""
    result = TranslationResult(translation="дом")
    assert result.translation == "дом"


def test_translation_result_missing_field() -> None:
    """Test TranslationResult raises ValidationError on missing field."""
    with pytest.raises(ValidationError):
        TranslationResult()


def test_all_models_accept_empty_strings() -> None:
    """Test all models accept empty strings (per architecture)."""
    extracted = ExtractedText(text="")
    word = WordEntry(normalized_form="", word_type="")
    result = TranslationResult(translation="")

    assert extracted.text == ""
    assert word.normalized_form == ""
    assert word.word_type == ""
    assert result.translation == ""
