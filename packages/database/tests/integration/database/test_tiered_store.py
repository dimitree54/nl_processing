"""Integration tests for TieredExerciseProgressStore against real Neon PostgreSQL."""

import os
import uuid

from nl_processing.core.models import Language
import pytest
import pytest_asyncio

from nl_processing.database.backend._neon_tiered import create_tiered_tables
from nl_processing.database.backend.neon import NeonBackend
from nl_processing.database.tiered_progress import TieredExerciseProgressStore


@pytest.fixture
def user_id() -> str:
    """Generate unique user ID for test isolation."""
    return f"test_user_{uuid.uuid4()}"


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def tiered_schema(integration_schema_ready: None) -> None:  # noqa: ARG001
    """Ensure extra tiered tables exist once per module."""
    backend = NeonBackend(os.environ["DATABASE_URL"])
    conn = await backend._connect()  # noqa: SLF001
    try:
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS user_word_exercise_scores_nl_ru_typing "
            "(id SERIAL PRIMARY KEY, user_id VARCHAR NOT NULL, "
            "source_word_id INTEGER NOT NULL, score INTEGER NOT NULL DEFAULT 0, "
            "updated_at TIMESTAMP NOT NULL DEFAULT NOW(), UNIQUE(user_id, source_word_id))"
        )
        await create_tiered_tables(conn, [("nl", "ru")])
    finally:
        await conn.close()


@pytest.fixture
def tiered_store(
    neon_backend: NeonBackend,
    tiered_schema: None,  # noqa: ARG001
    user_id: str,
) -> TieredExerciseProgressStore:
    """Create tiered store with test isolation."""
    return TieredExerciseProgressStore(
        user_id=user_id,
        source_language=Language.NL,
        target_language=Language.RU,
        mode_slug="tiered_mode",
        exercise_types=["flashcard", "typing"],
        backend=neon_backend,
    )


class TestTieredExerciseProgressStore:
    """Integration tests for tiered exercise progress store."""

    async def test_constructor_validation(self, neon_backend: NeonBackend) -> None:
        """Test constructor validation."""
        with pytest.raises(ValueError, match="mode_slug must be a non-empty string"):
            TieredExerciseProgressStore(
                user_id="test",
                source_language=Language.NL,
                target_language=Language.RU,
                mode_slug="",
                exercise_types=["flashcard"],
                backend=neon_backend,
            )

        # Empty exercise_types should raise
        with pytest.raises(ValueError, match="exercise_types must be a non-empty list"):
            TieredExerciseProgressStore(
                user_id="test",
                source_language=Language.NL,
                target_language=Language.RU,
                mode_slug="test_mode",
                exercise_types=[],
                backend=neon_backend,
            )

        # Whitespace-only mode_slug should raise
        with pytest.raises(ValueError, match="mode_slug must be a non-empty string"):
            TieredExerciseProgressStore(
                user_id="test",
                source_language=Language.NL,
                target_language=Language.RU,
                mode_slug="   ",
                exercise_types=["flashcard"],
                backend=neon_backend,
            )

    async def test_empty_vocabulary_returns_empty_candidates(self, tiered_store: TieredExerciseProgressStore) -> None:
        """Empty vocabulary returns empty candidates list."""
        candidates = await tiered_store.get_tiered_candidates()
        assert candidates == []

    async def test_empty_vocabulary_returns_zero_progress(self, tiered_store: TieredExerciseProgressStore) -> None:
        """Empty vocabulary returns zero progress summary."""
        summary = await tiered_store.get_tiered_progress_summary()
        assert summary.total_words == 0
        assert summary.fully_completed_words == 0
        assert summary.completion_ratio == 0.0

    async def test_empty_vocabulary_returns_empty_snapshot(self, tiered_store: TieredExerciseProgressStore) -> None:
        """Empty vocabulary returns empty snapshot."""
        snapshot = await tiered_store.export_tiered_snapshot()
        assert snapshot == []

    async def test_basic_tiered_functionality(
        self, neon_backend: NeonBackend, tiered_store: TieredExerciseProgressStore, user_id: str
    ) -> None:
        """Test basic tiered store functionality."""
        # Add test word to corpus with unique ID to avoid conflicts
        unique_suffix = uuid.uuid4().hex[:8]
        source_word = f"test_{unique_suffix}"
        target_word = f"тест_{unique_suffix}"
        source_word_id = await neon_backend.add_word("nl", source_word, "noun")
        target_word_id = await neon_backend.add_word("ru", target_word, "noun")
        assert source_word_id is not None
        assert target_word_id is not None
        await neon_backend.add_translation_link("nl_ru", source_word_id, target_word_id)
        await neon_backend.add_user_word(user_id, source_word_id, "nl")

        # Test that we can get candidates (basic functionality)
        candidates = await tiered_store.get_tiered_candidates()
        assert len(candidates) >= 1
        candidate = next(c for c in candidates if c.source_word_id == source_word_id)
        assert candidate.scores == {"flashcard": 0, "typing": 0}
        assert candidate.in_repeat_mode is False

        # Test progress summary
        summary = await tiered_store.get_tiered_progress_summary()
        assert summary.total_words >= 1
        assert summary.fully_completed_words == 0  # No positive scores yet

        # Test snapshot export
        snapshot = await tiered_store.export_tiered_snapshot()
        assert len(snapshot) >= 1
        entry = next(e for e in snapshot if e.source_word_id == source_word_id)
        assert entry.target_word_id == target_word_id
        assert entry.scores == {"flashcard": 0, "typing": 0}

    async def test_apply_tiered_result_validation(self, tiered_store: TieredExerciseProgressStore) -> None:
        """Test apply_tiered_result parameter validation."""
        with pytest.raises(ValueError, match="Unknown exercise_type"):
            await tiered_store.apply_tiered_result(event_id="evt", source_word_id=1, exercise_type="unknown", delta=1)
        with pytest.raises(ValueError, match="delta must be"):
            await tiered_store.apply_tiered_result(event_id="evt", source_word_id=1, exercise_type="flashcard", delta=0)

        with pytest.raises(ValueError, match="delta must be"):
            await tiered_store.apply_tiered_result(event_id="evt", source_word_id=1, exercise_type="flashcard", delta=2)
