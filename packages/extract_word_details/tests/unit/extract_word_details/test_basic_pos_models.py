"""Unit tests for basic POS models: noun, verb, adjective, adverb."""

from pydantic import ValidationError
import pytest

from nl_processing.extract_word_details._base_models import SharedLearningFields
from nl_processing.extract_word_details.models import (
    NlRuAdjectiveDetails,
    NlRuAdverbDetails,
    NlRuNounDetails,
    NlRuVerbDetails,
)


class TestNlRuNounDetails:
    """Tests for Dutch noun details model."""

    def test_valid_construction(self, shared_fields: SharedLearningFields) -> None:
        """Test creating a valid noun details instance."""
        noun = NlRuNounDetails(
            article="de", plural="huizen", diminutive="huisje", gender_explanation="Мужской род", shared=shared_fields
        )
        assert noun.article == "de"
        assert noun.plural == "huizen"
        assert noun.diminutive == "huisje"
        assert noun.gender_explanation == "Мужской род"

    def test_serialization_round_trip(self, shared_fields: SharedLearningFields) -> None:
        """Test model_dump and model_validate round trip."""
        original = NlRuNounDetails(
            article="het", plural=None, diminutive="boekje", gender_explanation="Средний род", shared=shared_fields
        )
        data = original.model_dump()
        reconstructed = NlRuNounDetails.model_validate(data)
        assert reconstructed == original

    def test_missing_required_fields(self, shared_fields: SharedLearningFields) -> None:
        """Test validation error when required fields are missing."""
        with pytest.raises(ValidationError):
            NlRuNounDetails(
                article="de",
                shared=shared_fields,
                # Missing gender_explanation
            )


class TestNlRuVerbDetails:
    """Tests for Dutch verb details model."""

    def test_valid_construction(self, shared_fields: SharedLearningFields) -> None:
        """Test creating a valid verb details instance."""
        verb = NlRuVerbDetails(
            present_tense={"ik": "loop", "jij": "loopt", "hij": "loopt", "wij": "lopen", "zij": "lopen"},
            past_simple="liep",
            past_participle="gelopen",
            auxiliary="hebben",
            separable_prefix=None,
            conjugation_explanation="Сильный глагол",
            shared=shared_fields,
        )
        assert verb.present_tense["ik"] == "loop"
        assert verb.past_simple == "liep"
        assert verb.auxiliary == "hebben"
        assert verb.separable_prefix is None

    def test_serialization_round_trip(self, shared_fields: SharedLearningFields) -> None:
        """Test model_dump and model_validate round trip."""
        original = NlRuVerbDetails(
            present_tense={"ik": "ga", "jij": "gaat"},
            past_simple="ging",
            past_participle="gegaan",
            auxiliary="zijn",
            separable_prefix="uit",
            conjugation_explanation="Глагол движения",
            shared=shared_fields,
        )
        data = original.model_dump()
        reconstructed = NlRuVerbDetails.model_validate(data)
        assert reconstructed == original

    def test_missing_required_fields(self, shared_fields: SharedLearningFields) -> None:
        """Test validation error when required fields are missing."""
        with pytest.raises(ValidationError):
            NlRuVerbDetails(
                present_tense={"ik": "loop"},
                past_simple="liep",
                shared=shared_fields,
                # Missing past_participle, auxiliary, conjugation_explanation
            )


class TestNlRuAdjectiveDetails:
    """Tests for Dutch adjective details model."""

    def test_valid_construction(self, shared_fields: SharedLearningFields) -> None:
        """Test creating a valid adjective details instance."""
        adj = NlRuAdjectiveDetails(
            comparative="groter",
            superlative="grootst",
            inflected_form="grote",
            usage_explanation="Объяснение употребления",
            shared=shared_fields,
        )
        assert adj.comparative == "groter"
        assert adj.superlative == "grootst"
        assert adj.inflected_form == "grote"

    def test_serialization_round_trip(self, shared_fields: SharedLearningFields) -> None:
        """Test model_dump and model_validate round trip."""
        original = NlRuAdjectiveDetails(
            comparative=None,
            superlative=None,
            inflected_form="mooie",
            usage_explanation="Красивый",
            shared=shared_fields,
        )
        data = original.model_dump()
        reconstructed = NlRuAdjectiveDetails.model_validate(data)
        assert reconstructed == original


class TestNlRuAdverbDetails:
    """Tests for Dutch adverb details model."""

    def test_valid_construction(self, shared_fields: SharedLearningFields) -> None:
        """Test creating a valid adverb details instance."""
        adv = NlRuAdverbDetails(
            usage_context="Контекст употребления", position_in_sentence="Позиция в предложении", shared=shared_fields
        )
        assert adv.usage_context == "Контекст употребления"
        assert adv.position_in_sentence == "Позиция в предложении"

    def test_serialization_round_trip(self, shared_fields: SharedLearningFields) -> None:
        """Test model_dump and model_validate round trip."""
        original = NlRuAdverbDetails(
            usage_context="Наречие времени", position_in_sentence="В конце предложения", shared=shared_fields
        )
        data = original.model_dump()
        reconstructed = NlRuAdverbDetails.model_validate(data)
        assert reconstructed == original
