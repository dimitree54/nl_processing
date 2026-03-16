"""E2e tests for exercise progress: score persistence via ExerciseProgressStore."""

from uuid import uuid4

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database_core.backend.neon import NeonBackend
import pytest

from nl_processing.database.exercise_progress import ExerciseProgressStore
from tests.e2e.database.conftest import cleanup_service, make_service

_WORDS = [
    Word(normalized_form="tafel", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="stoel", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="lamp", word_type=PartOfSpeech.NOUN, language=Language.NL),
]

_EXERCISE_TYPES = ["flashcard"]


async def _add_and_translate(user_id: str, backend: NeonBackend) -> None:
    """Add words and wait for translations to complete."""
    service = make_service(user_id, backend=backend)
    await service.add_words(_WORDS)
    # Wait for background translations and surface any failures
    await cleanup_service(service)


def _make_store(
    user_id: str,
    backend: NeonBackend,
    exercise_types: list[str] | None = None,
) -> ExerciseProgressStore:
    """Create an ExerciseProgressStore with standard config."""
    return ExerciseProgressStore(
        user_id=user_id,
        source_language=Language.NL,
        target_language=Language.RU,
        exercise_types=exercise_types or _EXERCISE_TYPES,
        backend=backend,
    )


async def _word_id_map(store: ExerciseProgressStore) -> dict[str, int]:
    """Return mapping {normalized_form: source_word_id} from remote snapshot export."""
    snapshot = await store.export_remote_snapshot()
    return {entry.pair.source.normalized_form: entry.source_word_id for entry in snapshot}


@pytest.mark.asyncio
async def test_increment_and_retrieve_scores(db_ready: NeonBackend) -> None:
    """Increment scores for words and verify persistence via get_word_pairs_with_scores."""
    user_id = f"e2e_user_{uuid4()}"
    await _add_and_translate(user_id, db_ready)

    store = _make_store(user_id, db_ready)
    ids = await _word_id_map(store)

    await store.increment(source_word_id=ids["tafel"], exercise_type="flashcard", delta=1)
    await store.increment(source_word_id=ids["tafel"], exercise_type="flashcard", delta=1)
    await store.increment(source_word_id=ids["stoel"], exercise_type="flashcard", delta=-1)

    scored = await store.get_word_pairs_with_scores()
    scores_by_form = {sp.pair.source.normalized_form: sp.scores["flashcard"] for sp in scored}

    assert scores_by_form["tafel"] == 2
    assert scores_by_form["stoel"] == -1


@pytest.mark.asyncio
async def test_missing_scores_default_to_zero(db_ready: NeonBackend) -> None:
    """Words without explicit scores show 0 for configured exercise types."""
    user_id = f"e2e_user_{uuid4()}"
    await _add_and_translate(user_id, db_ready)

    store = _make_store(user_id, db_ready)
    scored = await store.get_word_pairs_with_scores()
    assert len(scored) == len(_WORDS)

    for sp in scored:
        assert sp.scores["flashcard"] == 0


@pytest.mark.asyncio
async def test_scores_persist_across_store_instances(db_ready: NeonBackend) -> None:
    """Scores written by one store instance are readable by another."""
    user_id = f"e2e_user_{uuid4()}"
    await _add_and_translate(user_id, db_ready)

    store_1 = _make_store(user_id, db_ready)
    ids = await _word_id_map(store_1)
    await store_1.increment(source_word_id=ids["tafel"], exercise_type="flashcard", delta=1)

    store_2 = _make_store(user_id, db_ready)
    scored = await store_2.get_word_pairs_with_scores()
    scores_by_form = {sp.pair.source.normalized_form: sp.scores["flashcard"] for sp in scored}

    assert scores_by_form["tafel"] == 1
    assert scores_by_form["stoel"] == 0
    assert scores_by_form["lamp"] == 0
