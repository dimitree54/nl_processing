"""E2e tests for exercise progress: score persistence via ExerciseProgressStore."""

from uuid import uuid4

from nl_processing.core.models import Language, PartOfSpeech, Word
import pytest

from nl_processing.database.exercise_progress import ExerciseProgressStore
from tests.e2e.database.conftest import make_service, wait_for_translations

_WORDS = [
    Word(normalized_form="tafel", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="stoel", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="lamp", word_type=PartOfSpeech.NOUN, language=Language.NL),
]

_EXERCISE_TYPES = ["flashcard"]


async def _add_and_translate(user_id: str) -> None:
    """Add words and wait for translations to complete."""
    service = make_service(user_id)
    await service.add_words(_WORDS)
    await wait_for_translations(len(_WORDS))


def _make_store(user_id: str, exercise_types: list[str] | None = None) -> ExerciseProgressStore:
    """Create an ExerciseProgressStore with standard config."""
    return ExerciseProgressStore(
        user_id=user_id,
        source_language=Language.NL,
        target_language=Language.RU,
        exercise_types=exercise_types or _EXERCISE_TYPES,
    )


async def _word_id_map(store: ExerciseProgressStore) -> dict[str, int]:
    """Return mapping {normalized_form: source_word_id} from the store."""
    scored = await store.get_word_pairs_with_scores()
    return {sp.pair.source.normalized_form: sp.source_word_id for sp in scored}


@pytest.mark.asyncio
@pytest.mark.usefixtures("db_ready")
async def test_increment_and_retrieve_scores() -> None:
    """Increment scores for words and verify persistence via get_word_pairs_with_scores."""
    user_id = f"e2e_user_{uuid4()}"
    await _add_and_translate(user_id)

    store = _make_store(user_id)
    ids = await _word_id_map(store)

    await store.increment(source_word_id=ids["tafel"], exercise_type="flashcard", delta=1)
    await store.increment(source_word_id=ids["tafel"], exercise_type="flashcard", delta=1)
    await store.increment(source_word_id=ids["stoel"], exercise_type="flashcard", delta=-1)

    scored = await store.get_word_pairs_with_scores()
    scores_by_form = {sp.pair.source.normalized_form: sp.scores["flashcard"] for sp in scored}

    assert scores_by_form["tafel"] == 2
    assert scores_by_form["stoel"] == -1


@pytest.mark.asyncio
@pytest.mark.usefixtures("db_ready")
async def test_missing_scores_default_to_zero() -> None:
    """Words without explicit scores show 0 for configured exercise types."""
    user_id = f"e2e_user_{uuid4()}"
    await _add_and_translate(user_id)

    store = _make_store(user_id)
    scored = await store.get_word_pairs_with_scores()
    assert len(scored) == len(_WORDS)

    for sp in scored:
        assert sp.scores["flashcard"] == 0


@pytest.mark.asyncio
@pytest.mark.usefixtures("db_ready")
async def test_scores_persist_across_store_instances() -> None:
    """Scores written by one store instance are readable by another."""
    user_id = f"e2e_user_{uuid4()}"
    await _add_and_translate(user_id)

    store_1 = _make_store(user_id)
    ids = await _word_id_map(store_1)
    await store_1.increment(source_word_id=ids["tafel"], exercise_type="flashcard", delta=1)

    store_2 = _make_store(user_id)
    scored = await store_2.get_word_pairs_with_scores()
    scores_by_form = {sp.pair.source.normalized_form: sp.scores["flashcard"] for sp in scored}

    assert scores_by_form["tafel"] == 1
    assert scores_by_form["stoel"] == 0
    assert scores_by_form["lamp"] == 0
