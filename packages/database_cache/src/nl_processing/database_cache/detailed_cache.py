"""DetailedWordCacheService providing pair-scoped read-through caching for detailed-word records."""

import json
import os
from pathlib import Path

from nl_processing.core.models import Language, Word
from nl_processing.database.detailed_models import DetailedWordRecord

from nl_processing.database_cache._detailed_local_store import DetailedLocalStore
from nl_processing.database_cache.detailed_ports import RemoteDetailedWordStorePort, SchemaVersionChecker


class DetailedWordCacheService:
    """Pair-scoped read-through caching service for detailed word records."""

    def __init__(
        self,
        source_language: Language,
        target_language: Language,
        remote_store: RemoteDetailedWordStorePort | None = None,
        local_store: DetailedLocalStore | None = None,
        schema_checker: SchemaVersionChecker | None = None,
        cache_dir: str | None = None,
    ) -> None:
        self._source_language = source_language
        self._target_language = target_language
        self._remote_store = remote_store
        self._schema_checker = schema_checker

        if local_store is None:
            if cache_dir is None:
                cache_dir = str(Path.cwd() / "cache")
            os.makedirs(cache_dir, exist_ok=True)
            db_name = f"{source_language.value}_{target_language.value}_details.db"
            db_path = os.path.join(cache_dir, db_name)
            self._local_store = DetailedLocalStore(db_path)
        else:
            self._local_store = local_store

    async def get_or_fetch_details(self, words: list[Word]) -> list[DetailedWordRecord]:
        """Get detailed word records from cache or fetch from remote store.

        Returns results in the same order as input words.
        """
        if not words:
            return []

        # Ensure local store is open
        await self._local_store.open()

        # Check local cache for each word
        hits: list[DetailedWordRecord] = []
        misses: list[Word] = []

        for word in words:
            cached_row = await self._local_store.get_cached_detail(word.normalized_form, word.word_type.value)

            if cached_row is not None:
                # Check schema version compatibility
                if self._schema_checker is not None and not self._schema_checker.is_compatible(
                    str(cached_row["schema_key"]), int(cached_row["schema_version"])
                ):
                    # Invalidate incompatible row
                    await self._local_store.delete_cached_detail(word.normalized_form, word.word_type.value)
                    misses.append(word)
                else:
                    # Valid hit
                    payload = json.loads(str(cached_row["payload"]))
                    record = DetailedWordRecord(
                        source_word=str(cached_row["source_word"]),
                        word_type=str(cached_row["word_type"]),
                        schema_key=str(cached_row["schema_key"]),
                        schema_version=int(cached_row["schema_version"]),
                        payload=payload,
                    )
                    hits.append(record)
            else:
                # Cache miss
                misses.append(word)

        # Fetch misses from remote store
        if misses:
            if self._remote_store is None:
                raise ValueError("No remote store available for cache misses")

            # This may raise - if it does, local state remains unchanged (FR-15)
            fetched_records = await self._remote_store.get_or_extract_details(misses)

            # Persist newly fetched records locally
            for record in fetched_records:
                payload_json = json.dumps(record.payload)
                await self._local_store.upsert_cached_detail(
                    record.source_word,
                    record.word_type,
                    record.schema_key,
                    record.schema_version,
                    payload_json,
                )

            # Add to hits
            hits.extend(fetched_records)

        # Sort results to match input order
        result_map = {(record.source_word, record.word_type): record for record in hits}
        results: list[DetailedWordRecord] = []

        for word in words:
            key = (word.normalized_form, word.word_type.value)
            if key in result_map:
                results.append(result_map[key])
            # Skip words that have no result from remote (some POS may be unsupported)

        return results
