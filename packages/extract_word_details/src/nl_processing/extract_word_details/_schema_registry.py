"""Versioned schema registry for detailed word models.

Provides centralized registration and lookup of POS-specific models
with schema versioning support.
"""

from dataclasses import dataclass

from pydantic import BaseModel


@dataclass(frozen=True)
class SchemaRegistryEntry:
    """Entry in the schema registry."""

    schema_key: str
    schema_version: int
    model_class: type[BaseModel]


class SchemaRegistry:
    """Registry for versioned schemas by language pair and POS.

    Schema keys follow the pattern: {src}_{tgt}_{pos}
    Example: nl_ru_noun, nl_ru_verb
    """

    def __init__(self) -> None:
        self._entries: dict[tuple[str, int], SchemaRegistryEntry] = {}
        self._current_versions: dict[str, int] = {}

    def register(self, schema_key: str, schema_version: int, model_class: type[BaseModel]) -> None:
        """Register a schema with the given key and version."""
        entry_key = (schema_key, schema_version)
        entry = SchemaRegistryEntry(schema_key=schema_key, schema_version=schema_version, model_class=model_class)

        self._entries[entry_key] = entry

        # Update current version if this is newer
        current = self._current_versions.get(schema_key, 0)
        if schema_version > current:
            self._current_versions[schema_key] = schema_version

    def get_entry(self, schema_key: str, schema_version: int) -> SchemaRegistryEntry:
        """Get registry entry by key and version.

        Raises:
            KeyError: If schema key or version is not found.
        """
        entry_key = (schema_key, schema_version)
        if entry_key not in self._entries:
            if schema_key not in self._current_versions:
                raise KeyError(f"Unknown schema key: {schema_key}")
            raise KeyError(f"Unknown schema version {schema_version} for key {schema_key}")

        return self._entries[entry_key]

    def get_current_version(self, schema_key: str) -> int:
        """Get the latest registered version for a schema key.

        Raises:
            KeyError: If schema key is not found.
        """
        if schema_key not in self._current_versions:
            raise KeyError(f"Unknown schema key: {schema_key}")

        return self._current_versions[schema_key]

    def is_compatible(self, schema_key: str, schema_version: int) -> bool:
        """Check if a schema version is registered."""
        entry_key = (schema_key, schema_version)
        return entry_key in self._entries

    def list_schemas(self) -> list[str]:
        """List all registered schema keys."""
        return list(self._current_versions.keys())
