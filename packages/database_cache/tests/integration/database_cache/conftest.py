"""Shared fixtures for database_cache integration tests (file-based SQLite, mocked remote)."""

from pathlib import Path

from nl_processing.core.models import Language, PartOfSpeech, Word, WordPair, WordPairSnapshot
import pytest

_NL = Language.NL
_RU = Language.RU


def make_word(form: str, pos: PartOfSpeech = PartOfSpeech.NOUN, lang: Language = _NL) -> Word:
    """Create a Word helper for integration tests."""
    return Word(normalized_form=form, word_type=pos, language=lang)


def make_scored_pair(
    source_form: str,
    target_form: str,
    source_word_id: int,
    scores: dict[str, int] | None = None,
) -> WordPairSnapshot:
    """Build a NL→RU snapshot payload for integration-level cache tests."""
    src = make_word(source_form, lang=_NL)
    tgt = make_word(target_form, lang=_RU)
    return WordPairSnapshot(
        pair=WordPair(source=src, target=tgt),
        scores=scores or {},
        source_word_id=source_word_id,
        target_word_id=source_word_id + 1000,
    )


class MockProgressStore:
    """Configurable fake remote progress sync port for integration tests.

    Supports per-call failure via ``apply_errors_by_call`` (list consumed FIFO)
    and a blanket ``apply_error`` fallback.
    """

    def __init__(self, snapshot: list[WordPairSnapshot] | None = None) -> None:
        self.snapshot: list[WordPairSnapshot] = snapshot or []
        self.applied_deltas: list[dict[str, str | int]] = []
        self.apply_error: Exception | None = None
        self.apply_errors_by_call: list[Exception | None] = []

    async def export_remote_snapshot(self) -> list[WordPairSnapshot]:
        return list(self.snapshot)

    async def apply_score_delta(
        self,
        event_id: str,
        source_word_id: int,
        exercise_type: str,
        delta: int,
    ) -> None:
        error = self._pick_error()
        if error is not None:
            raise error
        self.applied_deltas.append({
            "event_id": event_id,
            "source_word_id": source_word_id,
            "exercise_type": exercise_type,
            "delta": delta,
        })

    def _pick_error(self) -> Exception | None:
        """Return the next error to raise, or None if the call should succeed."""
        if self.apply_errors_by_call:
            return self.apply_errors_by_call.pop(0)
        return self.apply_error


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Return a path to a SQLite file inside the pytest tmp directory."""
    return tmp_path / "integration_cache.db"
