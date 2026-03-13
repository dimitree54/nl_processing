"""Unit tests for schema registry initialization."""

import pytest

from nl_processing.extract_word_details._base_models import (
    CommonPhrase,
    ExampleSentence,
    InterestingFact,
    SharedLearningFields,
    WordPartExplanation,
)
from nl_processing.extract_word_details._serializer import parse_payload, serialize_payload
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
from nl_processing.extract_word_details.models._registry_init import SCHEMA_REGISTRY


class TestSchemaRegistryInit:
    """Tests for schema registry initialization with all POS models."""

    def test_all_13_pos_registered(self) -> None:
        """Verify all 13 POS models are registered in the schema registry."""
        expected_schema_keys = [
            "nl_ru_noun",
            "nl_ru_verb",
            "nl_ru_adjective",
            "nl_ru_adverb",
            "nl_ru_preposition",
            "nl_ru_conjunction",
            "nl_ru_pronoun",
            "nl_ru_article",
            "nl_ru_numeral",
            "nl_ru_interjection",
            "nl_ru_proper_noun_person",
            "nl_ru_proper_noun_country",
            "nl_ru_phrase",
        ]

        for schema_key in expected_schema_keys:
            assert SCHEMA_REGISTRY.is_compatible(schema_key, 1), f"Schema key {schema_key} not registered"

    def test_schema_key_naming_convention(self) -> None:
        """Verify schema_key naming convention is correct for each POS."""
        expected_entries = [
            ("nl_ru_noun", NlRuNounDetails),
            ("nl_ru_verb", NlRuVerbDetails),
            ("nl_ru_adjective", NlRuAdjectiveDetails),
            ("nl_ru_adverb", NlRuAdverbDetails),
            ("nl_ru_preposition", NlRuPrepositionDetails),
            ("nl_ru_conjunction", NlRuConjunctionDetails),
            ("nl_ru_pronoun", NlRuPronounDetails),
            ("nl_ru_article", NlRuArticleDetails),
            ("nl_ru_numeral", NlRuNumeralDetails),
            ("nl_ru_interjection", NlRuInterjectionDetails),
            ("nl_ru_proper_noun_person", NlRuProperNounPersonDetails),
            ("nl_ru_proper_noun_country", NlRuProperNounCountryDetails),
            ("nl_ru_phrase", NlRuPhraseDetails),
        ]

        for schema_key, expected_model_class in expected_entries:
            entry = SCHEMA_REGISTRY.get_entry(schema_key, 1)
            assert entry.schema_key == schema_key
            assert entry.model_class == expected_model_class

    def test_all_versions_are_1(self) -> None:
        """Verify all registered models start at version 1."""
        schema_keys = [
            "nl_ru_noun",
            "nl_ru_verb",
            "nl_ru_adjective",
            "nl_ru_adverb",
            "nl_ru_preposition",
            "nl_ru_conjunction",
            "nl_ru_pronoun",
            "nl_ru_article",
            "nl_ru_numeral",
            "nl_ru_interjection",
            "nl_ru_proper_noun_person",
            "nl_ru_proper_noun_country",
            "nl_ru_phrase",
        ]

        for schema_key in schema_keys:
            current_version = SCHEMA_REGISTRY.get_current_version(schema_key)
            assert current_version == 1, f"Schema {schema_key} should have version 1, got {current_version}"

    @pytest.fixture
    def sample_shared_fields(self) -> SharedLearningFields:
        """Sample shared fields for testing serialization."""
        return SharedLearningFields(
            common_phrases=[CommonPhrase(phrase="test phrase", translation="тестовая фраза")],
            example_sentences=[ExampleSentence(dutch_sentence="Test.", russian_explanation="Тест.")],
            word_parts=[WordPartExplanation(part="test", explanation_russian="тестовый корень")],
            interesting_facts=[InterestingFact(fact_russian="интересный факт")],
        )

    def test_round_trip_serialization_noun(self, sample_shared_fields: SharedLearningFields) -> None:
        """Test round-trip serialization for noun model through registry."""
        original = NlRuNounDetails(
            article="de",
            plural="huizen",
            diminutive="huisje",
            gender_explanation="Мужской род",
            shared=sample_shared_fields,
        )

        # Serialize through registry
        payload = serialize_payload(original)

        # Parse back through registry
        reconstructed = parse_payload("nl_ru_noun", 1, payload, SCHEMA_REGISTRY)

        assert isinstance(reconstructed, NlRuNounDetails)
        assert reconstructed == original
