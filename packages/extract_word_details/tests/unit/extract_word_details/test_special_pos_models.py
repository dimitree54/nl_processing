"""Unit tests for special POS models: proper nouns and phrase."""

from nl_processing.extract_word_details._base_models import SharedLearningFields
from nl_processing.extract_word_details.models import (
    NlRuPhraseDetails,
    NlRuProperNounCountryDetails,
    NlRuProperNounPersonDetails,
)


class TestNlRuProperNounPersonDetails:
    """Tests for Dutch proper noun (person) details model."""

    def test_valid_construction(self, shared_fields: SharedLearningFields) -> None:
        """Test creating a valid proper noun person details instance."""
        person = NlRuProperNounPersonDetails(
            origin_explanation="Германское происхождение",
            cultural_context="Традиционное нидерландское имя",
            shared=shared_fields,
        )
        assert person.origin_explanation == "Германское происхождение"
        assert person.cultural_context == "Традиционное нидерландское имя"

    def test_serialization_round_trip(self, shared_fields: SharedLearningFields) -> None:
        """Test model_dump and model_validate round trip."""
        original = NlRuProperNounPersonDetails(
            origin_explanation="Библейское происхождение", cultural_context="Популярное в XX веке", shared=shared_fields
        )
        data = original.model_dump()
        reconstructed = NlRuProperNounPersonDetails.model_validate(data)
        assert reconstructed == original


class TestNlRuProperNounCountryDetails:
    """Tests for Dutch proper noun (country) details model."""

    def test_valid_construction(self, shared_fields: SharedLearningFields) -> None:
        """Test creating a valid proper noun country details instance."""
        country = NlRuProperNounCountryDetails(
            dutch_name="Nederland",
            russian_name="Нидерланды",
            nationality_adjective="Nederlands",
            nationality_noun="Nederlander",
            cultural_context="Королевство в Западной Европе",
            shared=shared_fields,
        )
        assert country.dutch_name == "Nederland"
        assert country.russian_name == "Нидерланды"
        assert country.nationality_adjective == "Nederlands"
        assert country.nationality_noun == "Nederlander"

    def test_serialization_round_trip(self, shared_fields: SharedLearningFields) -> None:
        """Test model_dump and model_validate round trip."""
        original = NlRuProperNounCountryDetails(
            dutch_name="Duitsland",
            russian_name="Германия",
            nationality_adjective="Duits",
            nationality_noun="Duitser",
            cultural_context="Соседняя страна",
            shared=shared_fields,
        )
        data = original.model_dump()
        reconstructed = NlRuProperNounCountryDetails.model_validate(data)
        assert reconstructed == original


class TestNlRuPhraseDetails:
    """Tests for Dutch phrase details model."""

    def test_valid_construction(self, shared_fields: SharedLearningFields) -> None:
        """Test creating a valid phrase details instance."""
        phrase = NlRuPhraseDetails(
            literal_translation="дословный перевод",
            figurative_meaning="переносное значение",
            usage_context="контекст употребления",
            shared=shared_fields,
        )
        assert phrase.literal_translation == "дословный перевод"
        assert phrase.figurative_meaning == "переносное значение"
        assert phrase.usage_context == "контекст употребления"

    def test_serialization_round_trip(self, shared_fields: SharedLearningFields) -> None:
        """Test model_dump and model_validate round trip."""
        original = NlRuPhraseDetails(
            literal_translation="масло на голове иметь",
            figurative_meaning="чувствовать вину",
            usage_context="разговорная речь",
            shared=shared_fields,
        )
        data = original.model_dump()
        reconstructed = NlRuPhraseDetails.model_validate(data)
        assert reconstructed == original
