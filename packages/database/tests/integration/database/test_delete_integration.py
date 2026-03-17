"""Integration tests for delete behavior against real Neon."""

from nl_processing.core.models import PartOfSpeech
from nl_processing.database_core.backend.neon import NeonBackend
import pytest

from nl_processing.database.exceptions import WordNotFoundError
from nl_processing.database.service import DatabaseService
from tests.integration.database.conftest import (
    make_seeded_word_pair,
    make_seeded_word_set,
    make_unique_user_id,
    seed_word_scores,
)


@pytest.mark.asyncio
async def test_delete_word_removes_user_membership(
    neon_backend: NeonBackend,
    make_seeded_word_pair: make_seeded_word_pair,
) -> None:
    """delete_word removes user membership but preserves corpus and translation."""
    user_id = make_unique_user_id()
    other_user_id = make_unique_user_id()

    # Seed same word for two users
    word_pair_user1 = await make_seeded_word_pair(source_form="huis", target_form="house", user_id=user_id)
    await make_seeded_word_pair(source_form="huis", target_form="house", user_id=other_user_id)

    service_1 = DatabaseService(user_id=user_id, backend=neon_backend)
    service_2 = DatabaseService(user_id=other_user_id, backend=neon_backend)

    # Both users can see the word initially
    pairs_1_before = await service_1.get_words()
    pairs_2_before = await service_2.get_words()
    assert len(pairs_1_before) == 1
    assert len(pairs_2_before) == 1

    # User 1 deletes their membership
    await service_1.delete_word(word_pair_user1.source_word_id)

    # User 1 can no longer see the word, but user 2 still can
    pairs_1_after = await service_1.get_words()
    pairs_2_after = await service_2.get_words()
    assert len(pairs_1_after) == 0
    assert len(pairs_2_after) == 1

    # Verify corpus and translation link still exist (via user 2's access)
    assert pairs_2_after[0].source.normalized_form == "huis"
    assert pairs_2_after[0].target.normalized_form == "house"


@pytest.mark.asyncio
async def test_delete_word_removes_exercise_scores(
    neon_backend: NeonBackend,
    make_seeded_word_pair: make_seeded_word_pair,
    seed_word_scores: seed_word_scores,
) -> None:
    """delete_word removes associated exercise scores."""
    user_id = make_unique_user_id()

    # Seed word with scores
    word_pair = await make_seeded_word_pair(source_form="tafel", target_form="table", user_id=user_id)
    await seed_word_scores(
        source_word_id=word_pair.source_word_id,
        user_id=user_id,
        scores={"flashcard": 5},
    )

    service = DatabaseService(user_id=user_id, backend=neon_backend)

    # Verify score exists before deletion
    score_table = "nl_ru_flashcard"
    scores_before = await neon_backend.get_user_exercise_scores(score_table, user_id, [word_pair.source_word_id])
    assert len(scores_before) == 1
    assert scores_before[0]["score"] == 5

    # Delete the word with exercise types
    await service.delete_word(word_pair.source_word_id, exercise_types=["flashcard"])

    # Verify score is removed
    scores_after = await neon_backend.get_user_exercise_scores(score_table, user_id, [word_pair.source_word_id])
    assert len(scores_after) == 0  # No records when score is deleted


@pytest.mark.asyncio
async def test_delete_word_not_found_raises_error(
    neon_backend: NeonBackend,
) -> None:
    """delete_word raises WordNotFoundError for word not in user's vocabulary."""
    user_id = make_unique_user_id()
    service = DatabaseService(user_id=user_id, backend=neon_backend)

    nonexistent_id = 999999
    with pytest.raises(WordNotFoundError) as exc_info:
        await service.delete_word(nonexistent_id)

    assert "not in user's vocabulary" in str(exc_info.value)
    assert str(nonexistent_id) in str(exc_info.value)


@pytest.mark.asyncio
async def test_delete_words_bulk_operation(
    neon_backend: NeonBackend,
    make_seeded_word_set: make_seeded_word_set,
) -> None:
    """delete_words removes multiple words in one operation."""
    user_id = make_unique_user_id()

    # Seed multiple words
    word_specs = [
        ("word1", "target1", PartOfSpeech.NOUN),
        ("word2", "target2", PartOfSpeech.NOUN),
        ("word3", "target3", PartOfSpeech.VERB),
    ]
    pairs = await make_seeded_word_set(word_specs=word_specs, user_id=user_id)

    service = DatabaseService(user_id=user_id, backend=neon_backend)

    # Verify all words exist
    all_pairs = await service.get_words()
    assert len(all_pairs) == 3

    # Delete first two words
    word_ids_to_delete = [pairs[0].source_word_id, pairs[1].source_word_id]
    await service.delete_words(word_ids_to_delete)

    # Verify only third word remains
    remaining_pairs = await service.get_words()
    assert len(remaining_pairs) == 1
    assert remaining_pairs[0].source.normalized_form == "word3"


@pytest.mark.asyncio
async def test_delete_words_empty_list_noop(
    neon_backend: NeonBackend,
    make_seeded_word_pair: make_seeded_word_pair,
) -> None:
    """delete_words with empty list does nothing."""
    user_id = make_unique_user_id()

    # Seed one word
    await make_seeded_word_pair(source_form="test", target_form="test_target", user_id=user_id)

    service = DatabaseService(user_id=user_id, backend=neon_backend)

    pairs_before = await service.get_words()
    assert len(pairs_before) == 1

    # Delete empty list
    await service.delete_words([])

    # Nothing should change
    pairs_after = await service.get_words()
    assert len(pairs_after) == 1


@pytest.mark.asyncio
async def test_delete_word_user_isolation(
    neon_backend: NeonBackend,
    make_seeded_word_pair: make_seeded_word_pair,
) -> None:
    """Cannot delete another user's word."""
    user_a = make_unique_user_id()
    user_b = make_unique_user_id()

    # Seed word for user A
    user_a_pair = await make_seeded_word_pair(source_form="private", target_form="private_target", user_id=user_a)

    # User B tries to delete user A's word
    service_b = DatabaseService(user_id=user_b, backend=neon_backend)

    with pytest.raises(WordNotFoundError) as exc_info:
        await service_b.delete_word(user_a_pair.source_word_id)

    assert "not in user's vocabulary" in str(exc_info.value)

    # Verify user A's word is still there
    service_a = DatabaseService(user_id=user_a, backend=neon_backend)
    pairs_a = await service_a.get_words()
    assert len(pairs_a) == 1
