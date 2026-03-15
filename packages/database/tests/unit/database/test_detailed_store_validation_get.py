"""Unit tests for DetailedWordStore payload validation in get_details()."""

import json

from nl_processing.core.models import Language, PartOfSpeech, Word
import pytest

from nl_processing.database.detailed_exceptions import PayloadValidationError, SchemaVersionError
from nl_processing.database.detailed_store import DetailedWordStore
from tests.unit.database.conftest import FakeValidator, add_word_with_detail
from tests.unit.database.mock_backend import MockBackend


class TestDetailedWordStoreValidationGet:
    """Test DetailedWordStore validation in get_details()."""

    @pytest.fixture
    def store_with_validator(self, detailed_backend: MockBackend) -> tuple[DetailedWordStore, FakeValidator]:
        """Create a DetailedWordStore with validator."""
        validator = FakeValidator()
        store = DetailedWordStore(
            source_language=Language.NL,
            target_language=Language.RU,
            backend=detailed_backend,
            payload_validator=validator,
        )
        return store, validator

    async def test_get_details_with_validator_called(
        self,
        store_with_validator: tuple[DetailedWordStore, FakeValidator],
        detailed_backend: MockBackend,
    ) -> None:
        """Test get_details with validator - validator called for each returned record."""
        store, validator = store_with_validator

        word_id, payload = await add_word_with_detail(detailed_backend)
        word = Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL)
        result = await store.get_details([word])

        # Verify result
        assert len(result) == 1
        assert result[0].source_word == "hond"

        # Verify validator was called
        assert len(validator.calls) == 1
        assert validator.calls[0] == ("nl_ru_noun", 1, payload)

    async def test_get_details_validator_schema_version_error_propagates(self, detailed_backend: MockBackend) -> None:
        """Test get_details with validator raising SchemaVersionError - error propagates."""
        # Create validator that raises error
        error_validator = FakeValidator(SchemaVersionError("Unknown schema"))
        store = DetailedWordStore(
            source_language=Language.NL,
            target_language=Language.RU,
            backend=detailed_backend,
            payload_validator=error_validator,
        )

        # Add word and details
        word_id = await detailed_backend.add_word("nl", "hond", "noun")
        assert word_id is not None
        payload = {"article": "de"}
        await detailed_backend.upsert_word_details(
            "word_details_nl_ru", word_id, "noun", "unknown_schema", 1, json.dumps(payload)
        )

        word = Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL)

        # Verify error propagates
        with pytest.raises(SchemaVersionError, match="Unknown schema"):
            await store.get_details([word])

    async def test_get_details_validator_payload_validation_error_propagates(
        self, detailed_backend: MockBackend
    ) -> None:
        """Test get_details with validator raising PayloadValidationError - error propagates."""
        # Create validator that raises error
        error_validator = FakeValidator(PayloadValidationError("Invalid payload"))
        store = DetailedWordStore(
            source_language=Language.NL,
            target_language=Language.RU,
            backend=detailed_backend,
            payload_validator=error_validator,
        )

        # Add word and details
        word_id = await detailed_backend.add_word("nl", "hond", "noun")
        assert word_id is not None
        payload = {"invalid": "data"}
        await detailed_backend.upsert_word_details(
            "word_details_nl_ru", word_id, "noun", "nl_ru_noun", 1, json.dumps(payload)
        )

        word = Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL)

        # Verify error propagates
        with pytest.raises(PayloadValidationError, match="Invalid payload"):
            await store.get_details([word])

    async def test_no_validator_injected_no_validation_calls(self, detailed_backend: MockBackend) -> None:
        """Test no validator injected - no validation calls."""
        # Create store without validator
        store = DetailedWordStore(
            source_language=Language.NL,
            target_language=Language.RU,
            backend=detailed_backend,
        )

        # Add word and details
        word_id = await detailed_backend.add_word("nl", "hond", "noun")
        assert word_id is not None
        payload = {"article": "de"}
        await detailed_backend.upsert_word_details(
            "word_details_nl_ru", word_id, "noun", "nl_ru_noun", 1, json.dumps(payload)
        )

        word = Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL)
        result = await store.get_details([word])

        # Verify result works without validator
        assert len(result) == 1
        assert result[0].source_word == "hond"
