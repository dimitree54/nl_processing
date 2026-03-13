"""DetailedWordStore — pair-specific detailed-word persistence surface.

Provides get_details() and get_or_extract_details() methods for persisting
and retrieving detailed word records with schema metadata and JSON payloads.
"""

import json

from nl_processing.core.models import Language, Word

from nl_processing.database._database_config import read_database_url
from nl_processing.database._payload_parsing import parse_payload_from_backend
from nl_processing.database._validation import validate_payload_if_configured
from nl_processing.database.backend.abstract import AbstractBackend
from nl_processing.database.backend.neon import NeonBackend
from nl_processing.database.detailed_exceptions import (
    SourceWordNotFoundError,
)
from nl_processing.database.detailed_models import DetailedWordRecord
from nl_processing.database.detailed_ports import DetailedWordExtractorPort, PayloadValidatorPort
from nl_processing.database.logging import get_logger

_logger = get_logger("detailed_store")


class DetailedWordStore:
    """Async service for pair-specific detailed-word persistence."""

    def __init__(
        self,
        *,
        source_language: Language,
        target_language: Language,
        backend: AbstractBackend | None = None,
        extractor: DetailedWordExtractorPort | None = None,
        payload_validator: PayloadValidatorPort | None = None,
    ) -> None:
        if backend is None:
            database_url = read_database_url()
            self._backend: AbstractBackend = NeonBackend(database_url)
        else:
            self._backend = backend
        self._extractor = extractor
        self._payload_validator = payload_validator
        self._source_language = source_language
        self._target_language = target_language
        self._source_table = source_language.value
        self._details_table = f"word_details_{source_language.value}_{target_language.value}"

    async def get_details(self, words: list[Word]) -> list[DetailedWordRecord]:
        """Return persisted detailed records. Raise SourceWordNotFoundError for unknown words."""
        if not words:
            return []

        result = []
        for word in words:
            # Get canonical source word ID
            source_word = await self._backend.get_word(self._source_table, word.normalized_form)
            if source_word is None:
                msg = f"Source word '{word.normalized_form}' not found in corpus"
                raise SourceWordNotFoundError(msg)

            source_word_id = int(source_word["id"])
            word_type = word.word_type.value

            # Get detailed record
            detail_row = await self._backend.get_word_details(self._details_table, source_word_id, word_type)
            if detail_row is not None:
                payload_raw = detail_row["payload"]
                payload = parse_payload_from_backend(payload_raw)

                # Validate payload on read path
                validate_payload_if_configured(
                    self._payload_validator,
                    str(detail_row["schema_key"]),
                    int(detail_row["schema_version"]),
                    payload,
                )

                result.append(
                    DetailedWordRecord(
                        source_word=word.normalized_form,
                        word_type=word_type,
                        schema_key=str(detail_row["schema_key"]),
                        schema_version=int(detail_row["schema_version"]),
                        payload=payload,  # asyncpg returns JSONB as dict, mock as string
                    )
                )

        return result

    async def get_or_extract_details(self, words: list[Word]) -> list[DetailedWordRecord]:
        """Read first, extract misses, persist, return merged in input order."""
        if not words:
            return []

        if self._extractor is None:
            msg = "get_or_extract_details requires an extractor"
            raise ValueError(msg)

        # Build lookup of words with their canonical IDs
        word_id_map: dict[tuple[str, str], tuple[Word, int]] = {}
        for word in words:
            source_word = await self._backend.get_word(self._source_table, word.normalized_form)
            if source_word is None:
                msg = f"Source word '{word.normalized_form}' not found in corpus"
                raise SourceWordNotFoundError(msg)
            word_id_map[(word.normalized_form, word.word_type.value)] = (word, int(source_word["id"]))

        # Batch query for existing details
        source_word_ids_and_types = [
            (source_word_id, word.word_type.value) for word, source_word_id in word_id_map.values()
        ]
        existing_rows = await self._backend.get_word_details_batch(self._details_table, source_word_ids_and_types)

        # Build lookup of existing records
        # Contains both backend rows and constructed rows with JsonValue payload
        existing_lookup = {(int(row["source_word_id"]), str(row["word_type"])): row for row in existing_rows}

        # Find misses and extract them
        missing_words = []
        for word, source_word_id in word_id_map.values():
            key = (source_word_id, word.word_type.value)
            if key not in existing_lookup:
                missing_words.append(word)

        if missing_words:
            extracted_records = await self._extractor.extract(missing_words)
            for record in extracted_records:
                # Validate payload before persisting
                validate_payload_if_configured(
                    self._payload_validator, record.schema_key, record.schema_version, record.payload
                )

                # Find the source word ID for this record
                word_key = (record.source_word, record.word_type)
                if word_key in word_id_map:
                    _, source_word_id = word_id_map[word_key]

                    # Persist the extracted record
                    payload_json = json.dumps(record.payload)
                    await self._backend.upsert_word_details(
                        self._details_table,
                        source_word_id,
                        record.word_type,
                        record.schema_key,
                        record.schema_version,
                        payload_json,
                    )

                    # Add to existing lookup for return
                    existing_lookup[(source_word_id, record.word_type)] = {
                        "source_word_id": source_word_id,
                        "word_type": record.word_type,
                        "schema_key": record.schema_key,
                        "schema_version": record.schema_version,
                        "payload": record.payload,
                    }

        # Build results in input order
        result = []
        for word in words:
            word_key = (word.normalized_form, word.word_type.value)
            if word_key in word_id_map:
                _, source_word_id = word_id_map[word_key]
                detail_key = (source_word_id, word.word_type.value)

                if detail_key in existing_lookup:
                    detail_row = existing_lookup[detail_key]
                    payload_raw = detail_row["payload"]
                    payload = parse_payload_from_backend(payload_raw)

                    # Validate payload on read path
                    validate_payload_if_configured(
                        self._payload_validator,
                        str(detail_row["schema_key"]),
                        int(detail_row["schema_version"]),
                        payload,
                    )

                    result.append(
                        DetailedWordRecord(
                            source_word=word.normalized_form,
                            word_type=word.word_type.value,
                            schema_key=str(detail_row["schema_key"]),
                            schema_version=int(detail_row["schema_version"]),
                            payload=payload,
                        )
                    )

        return result
