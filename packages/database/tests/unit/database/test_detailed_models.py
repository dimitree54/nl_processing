"""Tests for detailed word models, ports, and exceptions."""

from nl_processing.core.models import Word
from nl_processing.database_core.exceptions import DatabaseError
import pytest

from nl_processing.database.detailed_exceptions import (
    PayloadValidationError,
    SchemaVersionError,
    SourceWordNotFoundError,
)
from nl_processing.database.detailed_models import DetailedWordRecord
from nl_processing.database.detailed_ports import DetailedWordExtractorPort


class TestDetailedWordRecord:
    """Test DetailedWordRecord model."""

    def test_valid_instance_creation(self) -> None:
        """Test creation with valid data."""
        record = DetailedWordRecord(
            source_word="hond",
            word_type="noun",
            schema_key="nl_ru_noun",
            schema_version=1,
            payload={"article": "de", "plural": "honden"},
        )

        assert record.source_word == "hond"
        assert record.word_type == "noun"
        assert record.schema_key == "nl_ru_noun"
        assert record.schema_version == 1
        assert record.payload == {"article": "de", "plural": "honden"}

    def test_serialization(self) -> None:
        """Test model serialization to dict."""
        record = DetailedWordRecord(
            source_word="kat", word_type="noun", schema_key="nl_ru_noun", schema_version=2, payload={"article": "de"}
        )

        result = record.model_dump()

        assert result == {
            "source_word": "kat",
            "word_type": "noun",
            "schema_key": "nl_ru_noun",
            "schema_version": 2,
            "payload": {"article": "de"},
        }

    def test_empty_payload_allowed(self) -> None:
        """Test that empty payload dict is valid."""
        record = DetailedWordRecord(
            source_word="test", word_type="verb", schema_key="nl_ru_verb", schema_version=1, payload={}
        )

        assert record.payload == {}

    def test_missing_fields_validation(self) -> None:
        """Test pydantic validation for missing required fields."""
        with pytest.raises(ValueError):
            DetailedWordRecord(word_type="noun", schema_key="nl_ru_noun", schema_version=1, payload={})


class TestDetailedWordExtractorPort:
    """Test DetailedWordExtractorPort protocol."""

    def test_runtime_checkable(self) -> None:
        """Test that the protocol is runtime checkable."""

        class MockExtractor:
            async def extract(self, words: list[Word]) -> list[DetailedWordRecord]:  # noqa: ARG002
                return []

        extractor = MockExtractor()
        assert isinstance(extractor, DetailedWordExtractorPort)

    def test_non_conforming_class_fails_check(self) -> None:
        """Test that non-conforming classes fail isinstance check."""

        class NonConformingClass:
            def some_other_method(self) -> None:
                pass

        instance = NonConformingClass()
        assert not isinstance(instance, DetailedWordExtractorPort)


class TestDetailedExceptions:
    """Test detailed word exception classes."""

    def test_source_word_not_found_error_inheritance(self) -> None:
        """Test SourceWordNotFoundError inherits from DatabaseError."""
        error = SourceWordNotFoundError("Word not found")
        assert isinstance(error, DatabaseError)
        assert str(error) == "Word not found"

    def test_schema_version_error_inheritance(self) -> None:
        """Test SchemaVersionError inherits from DatabaseError."""
        error = SchemaVersionError("Version mismatch")
        assert isinstance(error, DatabaseError)
        assert str(error) == "Version mismatch"

    def test_payload_validation_error_inheritance(self) -> None:
        """Test PayloadValidationError inherits from DatabaseError."""
        error = PayloadValidationError("Invalid payload")
        assert isinstance(error, DatabaseError)
        assert str(error) == "Invalid payload"

    def test_exceptions_can_be_raised_and_caught(self) -> None:
        """Test that exceptions can be raised and caught as DatabaseError."""
        with pytest.raises(DatabaseError):
            raise SourceWordNotFoundError("test")

        with pytest.raises(DatabaseError):
            raise SchemaVersionError("test")

        with pytest.raises(DatabaseError):
            raise PayloadValidationError("test")

    def test_exception_message_propagation(self) -> None:
        """Test that exception messages propagate correctly."""
        source_msg = "Source word 'test' not found"
        schema_msg = "Schema version 5 not supported"
        payload_msg = "Payload validation failed"

        try:
            raise SourceWordNotFoundError(source_msg)
        except DatabaseError as e:
            assert str(e) == source_msg

        try:
            raise SchemaVersionError(schema_msg)
        except DatabaseError as e:
            assert str(e) == schema_msg

        try:
            raise PayloadValidationError(payload_msg)
        except DatabaseError as e:
            assert str(e) == payload_msg
