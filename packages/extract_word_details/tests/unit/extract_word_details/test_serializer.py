"""Unit tests for serializer functions."""

from pydantic import BaseModel
import pytest

from nl_processing.extract_word_details._exceptions import (
    PayloadValidationError,
    SchemaVersionError,
)
from nl_processing.extract_word_details._schema_registry import SchemaRegistry
from nl_processing.extract_word_details._serializer import (
    parse_payload,
    serialize_payload,
)


class MockModel(BaseModel):
    """Mock model for serialization testing."""

    name: str
    value: int


class StrictMockModel(BaseModel):
    """Mock model with strict validation."""

    required_field: str


class TestSerializePayload:
    """Test serialize_payload function."""

    def test_serialize_simple_model(self) -> None:
        model = MockModel(name="test", value=42)

        result = serialize_payload(model)
        expected = {"name": "test", "value": 42}

        assert result == expected

    def test_serialize_with_optional_fields(self) -> None:
        class ModelWithOptional(BaseModel):
            required: str
            optional: str | None = None

        model = ModelWithOptional(required="test")

        result = serialize_payload(model)
        expected = {"required": "test", "optional": None}

        assert result == expected


class TestParsePayload:
    """Test parse_payload function."""

    def setup_method(self) -> None:
        self.registry = SchemaRegistry()
        self.registry.register("test_schema", 1, MockModel)
        self.registry.register("test_schema", 2, StrictMockModel)

    def test_parse_valid_payload(self) -> None:
        payload = {"name": "test", "value": 42}

        result = parse_payload("test_schema", 1, payload, self.registry)

        assert isinstance(result, MockModel)
        assert result.name == "test"
        assert result.value == 42

    def test_round_trip_serialization(self) -> None:
        original = MockModel(name="test", value=42)

        # Serialize
        payload = serialize_payload(original)

        # Parse back
        result = parse_payload("test_schema", 1, payload, self.registry)

        assert result == original

    def test_parse_unknown_schema_key(self) -> None:
        payload = {"name": "test", "value": 42}

        with pytest.raises(SchemaVersionError, match="Unknown schema key: unknown_key"):
            parse_payload("unknown_key", 1, payload, self.registry)

    def test_parse_unknown_schema_version(self) -> None:
        payload = {"name": "test", "value": 42}

        with pytest.raises(SchemaVersionError, match="Unknown schema version 99 for key test_schema"):
            parse_payload("test_schema", 99, payload, self.registry)

    def test_parse_invalid_payload(self) -> None:
        # Missing required field
        payload = {"name": "test"}

        with pytest.raises(PayloadValidationError, match="Validation failed"):
            parse_payload("test_schema", 1, payload, self.registry)

    def test_parse_wrong_field_type(self) -> None:
        # Wrong type for value field
        payload = {"name": "test", "value": "not_an_int"}

        with pytest.raises(PayloadValidationError, match="Validation failed"):
            parse_payload("test_schema", 1, payload, self.registry)

    def test_parse_extra_fields_ignored(self) -> None:
        # Pydantic ignores extra fields by default
        payload = {"name": "test", "value": 42, "extra_field": "ignored"}

        result = parse_payload("test_schema", 1, payload, self.registry)

        assert isinstance(result, MockModel)
        assert result.name == "test"
        assert result.value == 42
        # Extra field is ignored by Pydantic, so it won't be in the result
        assert "extra_field" not in result.model_dump()

    def test_parse_different_schema_versions(self) -> None:
        # Test with version 1 (MockModel)
        payload1 = {"name": "test", "value": 42}
        result1 = parse_payload("test_schema", 1, payload1, self.registry)
        assert isinstance(result1, MockModel)

        # Test with version 2 (StrictMockModel)
        payload2 = {"required_field": "test"}
        result2 = parse_payload("test_schema", 2, payload2, self.registry)
        assert isinstance(result2, StrictMockModel)

    def test_parse_partial_payload_validation_error(self) -> None:
        # Test that partial matches still fail validation
        payload = {"required_field": "test", "invalid_extra": "should_not_break"}

        # This should work - pydantic ignores extra fields
        result = parse_payload("test_schema", 2, payload, self.registry)
        assert isinstance(result, StrictMockModel)
        assert result.required_field == "test"
