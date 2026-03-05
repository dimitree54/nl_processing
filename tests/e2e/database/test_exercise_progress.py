"""E2e tests for exercise progress: score persistence via ExerciseProgressStore."""

from uuid import uuid4

import pytest

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database.exercise_progress import ExerciseProgressStore
from nl_processing.database.service import DatabaseService
from tests.e2e.database.conftest import wait_for_translations

_WORDS = [
    Word(normalized_form="tafel", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="stoel", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="lamp", word_type=PartOfSpeech.NOUN, language=Language.NL),
]


async def _add_and_translate(user_id: str) -> None:
    """Add words and wait for translations to complete."""
    service = DatabaseService(user_id=user_id)
    await service.add_words(_WORDS)
    await wait_for_translations(len(_WORDS))


@pytest.mark.asyncio
@pytest.mark.usefixtures("db_ready")
async def test_increment_and_retrieve_scores() -> None:
    """Increment scores for words and verify persistence via get_word_pairs_with_scores."""
    user_id = f"e2e_user_{uuid4()}"
    await _add_and_translate(user_id)

    store = ExerciseProgressStore(
        user_id=user_id,
        source_language=Language.NL,
        target_language=Language.RU,
    )

    await store.increment(_WORDS[0], "flashcard", 1)
    await store.increment(_WORDS[0], "flashcard", 1)
    await store.increment(_WORDS[1], "flashcard", -1)

    scored = await store.get_word_pairs_with_scores(["flashcard"])
    scores_by_form = {sp.pair.source.normalized_form: sp.scores["flashcard"] for sp in scored}

    assert scores_by_form["tafel"] == 2
    assert scores_by_form["stoel"] == -1


@pytest.mark.asyncio
@pytest.mark.usefixtures("db_ready")
async def test_missing_scores_default_to_zero() -> None:
    """Words without explicit scores show 0 for requested exercise types."""
    user_id = f"e2e_user_{uuid4()}"
    await _add_and_translate(user_id)

    store = ExerciseProgressStore(
        user_id=user_id,
        source_language=Language.NL,
        target_language=Language.RU,
    )

    scored = await store.get_word_pairs_with_scores(["flashcard", "typing"])
    assert len(scored) == len(_WORDS)

    for sp in scored:
        assert sp.scores["flashcard"] == 0
        assert sp.scores["typing"] == 0


@pytest.mark.asyncio
@pytest.mark.usefixtures("db_ready")
async def test_scores_persist_across_store_instances() -> None:
    """Scores written by one store instance are readable by another."""
    user_id = f"e2e_user_{uuid4()}"
    await _add_and_translate(user_id)

    store_1 = ExerciseProgressStore(
        user_id=user_id,
        source_language=Language.NL,
        target_language=Language.RU,
    )
    await store_1.increment(_WORDS[0], "typing", 1)

    store_2 = ExerciseProgressStore(
        user_id=user_id,
        source_language=Language.NL,
        target_language=Language.RU,
    )
    scored = await store_2.get_word_pairs_with_scores(["typing"])
    scores_by_form = {sp.pair.source.normalized_form: sp.scores["typing"] for sp in scored}

    assert scores_by_form["tafel"] == 1
    assert scores_by_form["stoel"] == 0
    assert scores_by_form["lamp"] == 0
