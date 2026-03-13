"""Unit tests for schema registry."""

from pydantic import BaseModel
import pytest

from nl_processing.extract_word_details._schema_registry import (
    SchemaRegistry,
    SchemaRegistryEntry,
)


class MockModel(BaseModel):
    """Mock model for registry testing."""

    field: str


class AnotherMockModel(BaseModel):
    """Another mock model for registry testing."""

    value: int


class TestSchemaRegistryEntry:
    """Test SchemaRegistryEntry dataclass."""

    def test_construction(self) -> None:
        entry = SchemaRegistryEntry(schema_key="nl_ru_test", schema_version=1, model_class=MockModel)

        assert entry.schema_key == "nl_ru_test"
        assert entry.schema_version == 1
        assert entry.model_class == MockModel

    def test_frozen(self) -> None:
        entry = SchemaRegistryEntry(schema_key="nl_ru_test", schema_version=1, model_class=MockModel)

        with pytest.raises(Exception):
            entry.schema_key = "different_key"


class TestSchemaRegistry:
    """Test SchemaRegistry class."""

    def test_empty_registry(self) -> None:
        registry = SchemaRegistry()

        with pytest.raises(KeyError, match="Unknown schema key: nl_ru_test"):
            registry.get_entry("nl_ru_test", 1)

        with pytest.raises(KeyError, match="Unknown schema key: nl_ru_test"):
            registry.get_current_version("nl_ru_test")

        assert not registry.is_compatible("nl_ru_test", 1)

    def test_register_single_version(self) -> None:
        registry = SchemaRegistry()

        registry.register("nl_ru_test", 1, MockModel)

        entry = registry.get_entry("nl_ru_test", 1)
        assert entry.schema_key == "nl_ru_test"
        assert entry.schema_version == 1
        assert entry.model_class == MockModel

        assert registry.get_current_version("nl_ru_test") == 1
        assert registry.is_compatible("nl_ru_test", 1)

    def test_register_multiple_versions(self) -> None:
        registry = SchemaRegistry()

        registry.register("nl_ru_test", 1, MockModel)
        registry.register("nl_ru_test", 2, AnotherMockModel)

        # Both versions should be available
        entry1 = registry.get_entry("nl_ru_test", 1)
        assert entry1.model_class == MockModel

        entry2 = registry.get_entry("nl_ru_test", 2)
        assert entry2.model_class == AnotherMockModel

        # Current version should be the latest
        assert registry.get_current_version("nl_ru_test") == 2

        assert registry.is_compatible("nl_ru_test", 1)
        assert registry.is_compatible("nl_ru_test", 2)

    def test_register_versions_out_of_order(self) -> None:
        registry = SchemaRegistry()

        # Register version 2 first, then version 1
        registry.register("nl_ru_test", 2, AnotherMockModel)
        registry.register("nl_ru_test", 1, MockModel)

        # Current version should still be 2 (the highest)
        assert registry.get_current_version("nl_ru_test") == 2

        # Both versions should work
        entry1 = registry.get_entry("nl_ru_test", 1)
        assert entry1.model_class == MockModel

        entry2 = registry.get_entry("nl_ru_test", 2)
        assert entry2.model_class == AnotherMockModel

    def test_register_multiple_schema_keys(self) -> None:
        registry = SchemaRegistry()

        registry.register("nl_ru_noun", 1, MockModel)
        registry.register("nl_ru_verb", 1, AnotherMockModel)

        entry1 = registry.get_entry("nl_ru_noun", 1)
        assert entry1.model_class == MockModel

        entry2 = registry.get_entry("nl_ru_verb", 1)
        assert entry2.model_class == AnotherMockModel

        assert registry.get_current_version("nl_ru_noun") == 1
        assert registry.get_current_version("nl_ru_verb") == 1

    def test_get_entry_unknown_schema_key(self) -> None:
        registry = SchemaRegistry()

        with pytest.raises(KeyError, match="Unknown schema key: unknown_key"):
            registry.get_entry("unknown_key", 1)

    def test_get_entry_unknown_version(self) -> None:
        registry = SchemaRegistry()
        registry.register("nl_ru_test", 1, MockModel)

        with pytest.raises(KeyError, match="Unknown schema version 2 for key nl_ru_test"):
            registry.get_entry("nl_ru_test", 2)

    def test_get_current_version_unknown_key(self) -> None:
        registry = SchemaRegistry()

        with pytest.raises(KeyError, match="Unknown schema key: unknown_key"):
            registry.get_current_version("unknown_key")

    def test_is_compatible_false_cases(self) -> None:
        registry = SchemaRegistry()
        registry.register("nl_ru_test", 1, MockModel)

        # Unknown key
        assert not registry.is_compatible("unknown_key", 1)

        # Unknown version
        assert not registry.is_compatible("nl_ru_test", 2)

    def test_schema_key_format(self) -> None:
        registry = SchemaRegistry()

        # Test typical schema key format
        registry.register("nl_ru_noun", 1, MockModel)
        registry.register("en_es_verb", 1, AnotherMockModel)

        assert registry.is_compatible("nl_ru_noun", 1)
        assert registry.is_compatible("en_es_verb", 1)
