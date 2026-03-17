"""Integration tests for get_words query behavior against real Neon."""

from nl_processing.core.models import PartOfSpeech
from nl_processing.database_core.backend.neon import NeonBackend
import pytest

from nl_processing.database.service import DatabaseService
from tests.integration.database.conftest import (
    make_seeded_word_pair,
    make_seeded_word_set,
    make_unique_user_id,
)


@pytest.mark.asyncio
async def test_get_words_translated_only_reads(
    neon_backend: NeonBackend,
    make_seeded_word_pair: make_seeded_word_pair,
) -> None:
    """get_words returns only translated word pairs, not untranslated."""
    user_id = make_unique_user_id()

    # Seed one translated and one untranslated word
    translated = await make_seeded_word_pair(source_form="huis", target_form="house", user_id=user_id)
    untranslated = await make_seeded_word_pair(source_form="boom", target_form=None, user_id=user_id)

    service = DatabaseService(user_id=user_id, backend=neon_backend)
    pairs = await service.get_words()

    # Should only include the translated word
    assert len(pairs) == 1
    assert pairs[0].source.normalized_form == translated.source_normalized_form
    assert pairs[0].target.normalized_form == translated.target_normalized_form

    # Verify untranslated word is not included
    source_forms = {p.source.normalized_form for p in pairs}
    assert untranslated.source_normalized_form not in source_forms


@pytest.mark.asyncio
async def test_get_words_user_isolation(
    neon_backend: NeonBackend,
    make_seeded_word_pair: make_seeded_word_pair,
) -> None:
    """get_words isolates words by user_id."""
    user_a = make_unique_user_id()
    user_b = make_unique_user_id()

    # Seed words for different users
    user_a_word = await make_seeded_word_pair(source_form="tafel", target_form="table", user_id=user_a)
    user_b_word = await make_seeded_word_pair(source_form="stoel", target_form="chair", user_id=user_b)

    # Each user should only see their own words
    service_a = DatabaseService(user_id=user_a, backend=neon_backend)
    pairs_a = await service_a.get_words()
    assert len(pairs_a) == 1
    assert pairs_a[0].source.normalized_form == user_a_word.source_normalized_form

    service_b = DatabaseService(user_id=user_b, backend=neon_backend)
    pairs_b = await service_b.get_words()
    assert len(pairs_b) == 1
    assert pairs_b[0].source.normalized_form == user_b_word.source_normalized_form


@pytest.mark.asyncio
async def test_get_words_word_type_filtering(
    neon_backend: NeonBackend,
    make_seeded_word_set: make_seeded_word_set,
) -> None:
    """get_words filters by word_type correctly."""
    user_id = make_unique_user_id()

    # Seed mixed word types
    word_specs = [
        ("huis", "house", PartOfSpeech.NOUN),
        ("groot", "big", PartOfSpeech.ADJECTIVE),
        ("lopen", "run", PartOfSpeech.VERB),
        ("auto", "car", PartOfSpeech.NOUN),
    ]
    await make_seeded_word_set(word_specs=word_specs, user_id=user_id)

    service = DatabaseService(user_id=user_id, backend=neon_backend)

    # Filter for nouns only
    noun_pairs = await service.get_words(word_type=PartOfSpeech.NOUN)
    assert len(noun_pairs) == 2
    noun_forms = {p.source.normalized_form for p in noun_pairs}
    assert noun_forms == {"huis", "auto"}

    # Filter for adjectives only
    adj_pairs = await service.get_words(word_type=PartOfSpeech.ADJECTIVE)
    assert len(adj_pairs) == 1
    assert adj_pairs[0].source.normalized_form == "groot"

    # Filter for verbs only
    verb_pairs = await service.get_words(word_type=PartOfSpeech.VERB)
    assert len(verb_pairs) == 1
    assert verb_pairs[0].source.normalized_form == "lopen"


@pytest.mark.asyncio
async def test_get_words_limit_parameter(
    neon_backend: NeonBackend,
    make_seeded_word_set: make_seeded_word_set,
) -> None:
    """get_words respects limit parameter."""
    user_id = make_unique_user_id()

    # Seed 5 translated words
    word_specs = [(f"word{i}", f"target{i}", PartOfSpeech.NOUN) for i in range(5)]
    await make_seeded_word_set(word_specs=word_specs, user_id=user_id)

    service = DatabaseService(user_id=user_id, backend=neon_backend)

    # Test different limits
    pairs_3 = await service.get_words(limit=3)
    assert len(pairs_3) == 3

    pairs_2 = await service.get_words(limit=2)
    assert len(pairs_2) == 2

    pairs_all = await service.get_words()
    assert len(pairs_all) == 5


@pytest.mark.asyncio
async def test_get_words_random_selection(
    neon_backend: NeonBackend,
    make_seeded_word_set: make_seeded_word_set,
) -> None:
    """get_words with random=True returns unique pairs without deterministic order."""
    user_id = make_unique_user_id()

    # Seed enough words to make randomness meaningful
    word_specs = [(f"word{i}", f"target{i}", PartOfSpeech.NOUN) for i in range(10)]
    await make_seeded_word_set(word_specs=word_specs, user_id=user_id)

    service = DatabaseService(user_id=user_id, backend=neon_backend)

    # Get random sample
    pairs = await service.get_words(limit=5, random=True)
    assert len(pairs) == 5

    # All pairs should be unique
    source_forms = [p.source.normalized_form for p in pairs]
    assert len(set(source_forms)) == 5

    # All forms should be from our seeded set
    expected_forms = {f"word{i}" for i in range(10)}
    actual_forms = set(source_forms)
    assert actual_forms.issubset(expected_forms)


@pytest.mark.asyncio
async def test_get_words_combined_filters(
    neon_backend: NeonBackend,
    make_seeded_word_set: make_seeded_word_set,
) -> None:
    """get_words works with combined word_type and limit filters."""
    user_id = make_unique_user_id()

    # Seed mixed types with more nouns than limit
    word_specs = [
        ("noun1", "target1", PartOfSpeech.NOUN),
        ("noun2", "target2", PartOfSpeech.NOUN),
        ("noun3", "target3", PartOfSpeech.NOUN),
        ("verb1", "vtarget1", PartOfSpeech.VERB),
        ("adj1", "atarget1", PartOfSpeech.ADJECTIVE),
    ]
    await make_seeded_word_set(word_specs=word_specs, user_id=user_id)

    service = DatabaseService(user_id=user_id, backend=neon_backend)

    # Get only 2 nouns
    pairs = await service.get_words(word_type=PartOfSpeech.NOUN, limit=2)
    assert len(pairs) == 2
    for pair in pairs:
        assert pair.source.word_type == PartOfSpeech.NOUN
