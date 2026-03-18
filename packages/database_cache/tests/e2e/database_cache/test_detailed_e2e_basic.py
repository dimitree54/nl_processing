"""Basic E2E test for DetailedWordCacheService with real Neon DB and SQLite."""

from pathlib import Path

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database.detailed_models import DetailedWordRecord
from nl_processing.database.detailed_store import DetailedWordStore
from nl_processing.database_core.backend.neon import NeonBackend
import pytest

from nl_processing.database_cache.detailed_cache import DetailedWordCacheService


class MockExtractor:
    """Mock extractor that returns synthetic DetailedWordRecord data."""

    def __init__(self) -> None:
        self.extraction_count = 0

    async def extract(self, words: list[Word]) -> list[DetailedWordRecord]:
        """Extract synthetic detailed records for testing."""
        self.extraction_count += 1

        records = []
        for word in words:
            # Create synthetic payload based on word
            if word.word_type == PartOfSpeech.NOUN:
                payload = {
                    "definition": f"definition of {word.normalized_form}",
                    "gender": "neuter",
                    "plural": f"{word.normalized_form}en",
                }
            else:
                payload = {
                    "definition": f"definition of {word.normalized_form}",
                    "type": word.word_type.value,
                }

            schema_key = f"{word.language.value}_ru_{word.word_type.value}"
            record = DetailedWordRecord(
                source_word=word.normalized_form,
                word_type=word.word_type.value,
                schema_key=schema_key,
                schema_version=1,
                payload=payload,
            )
            records.append(record)

        return records


@pytest.mark.asyncio
async def test_full_flow_with_real_backend(db_ready: NeonBackend, tmp_path: Path) -> None:
    """Full flow with real remote backend (Neon DB) and real SQLite."""
    mock_extractor = MockExtractor()

    remote_store = DetailedWordStore(
        source_language=Language.NL,
        target_language=Language.RU,
        backend=db_ready,
        extractor=mock_extractor,
    )

    cache_dir = str(tmp_path / "cache")
    service = DetailedWordCacheService(
        source_language=Language.NL,
        target_language=Language.RU,
        remote_store=remote_store,
        cache_dir=cache_dir,
    )

    try:
        test_word = Word(normalized_form="testword", word_type=PartOfSpeech.NOUN, language=Language.NL)

        # Insert source word into nl table
        await db_ready.add_word("nl", test_word.normalized_form, test_word.word_type.value)

        # First call: cache miss, should fetch from remote (which extracts via mock)
        result1 = await service.get_or_fetch_details([test_word])

        assert len(result1) == 1
        assert result1[0].source_word == "testword"
        assert result1[0].word_type == "noun"
        assert result1[0].schema_key == "nl_ru_noun"
        assert result1[0].payload["definition"] == "definition of testword"
        assert result1[0].payload["gender"] == "neuter"
        assert mock_extractor.extraction_count == 1

        # Second call: cache hit, should NOT call remote/extractor
        result2 = await service.get_or_fetch_details([test_word])

        assert len(result2) == 1
        assert result2[0].source_word == "testword"
        assert result2[0].word_type == "noun"
        assert result2[0].payload["definition"] == "definition of testword"
        assert mock_extractor.extraction_count == 1  # Should not increment
    finally:
        await service.close()
