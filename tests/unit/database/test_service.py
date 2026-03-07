"""Unit tests for DatabaseService and CachedDatabaseService."""

import asyncio

import pytest

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database.cached_service import CachedDatabaseService
from nl_processing.database.exceptions import ConfigurationError
from nl_processing.database.models import WordPair
from nl_processing.database.service import DatabaseService
from tests.unit.database.conftest import MockBackend

_HUIS = Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL)
_LOPEN = Word(normalized_form="lopen", word_type=PartOfSpeech.VERB, language=Language.NL)
_SNEL = Word(normalized_form="snel", word_type=PartOfSpeech.ADVERB, language=Language.NL)
_DOM = Word(normalized_form="dom", word_type=PartOfSpeech.NOUN, language=Language.RU)


# ---- DatabaseService.add_words ----


@pytest.mark.asyncio
async def test_add_words_new(db_service: DatabaseService) -> None:
    """All-new words populate new_words."""
    result = await db_service.add_words([_HUIS, _LOPEN])
    assert len(result.new_words) == 2
    assert result.existing_words == []


@pytest.mark.asyncio
async def test_add_words_existing(db_service: DatabaseService) -> None:
    """Second call marks words as existing."""
    await db_service.add_words([_HUIS])
    result = await db_service.add_words([_HUIS])
    assert result.new_words == []
    assert len(result.existing_words) == 1
    assert result.existing_words[0].normalized_form == "huis"


@pytest.mark.asyncio
async def test_add_words_mix(db_service: DatabaseService) -> None:
    """Mix of new and existing words populates both lists."""
    await db_service.add_words([_HUIS])
    result = await db_service.add_words([_HUIS, _LOPEN])
    assert len(result.existing_words) == 1
    assert len(result.new_words) == 1


@pytest.mark.asyncio
async def test_add_words_empty(db_service: DatabaseService) -> None:
    """Empty input returns empty result."""
    result = await db_service.add_words([])
    assert result.new_words == []
    assert result.existing_words == []


@pytest.mark.asyncio
async def test_add_words_creates_user_associations(db_service: DatabaseService, mock_backend: MockBackend) -> None:
    """add_words creates user-word associations in the backend."""
    await db_service.add_words([_HUIS, _LOPEN])
    assert len(mock_backend._user_words) == 2
    user_ids = [uid for uid, _, _ in mock_backend._user_words]
    assert all(uid == "u1" for uid in user_ids)


@pytest.mark.asyncio
async def test_add_words_triggers_translation(db_service: DatabaseService, mock_backend: MockBackend) -> None:
    """New words trigger background translation task."""
    await db_service.add_words([_HUIS])
    await asyncio.sleep(0.05)
    assert "HUIS" in mock_backend._words.get("ru", {}), "Translation should have stored uppercased word"


@pytest.mark.asyncio
async def test_add_words_uses_word_language_for_storage(
    db_service: DatabaseService,
    mock_backend: MockBackend,
) -> None:
    """Words are stored and associated under their own language."""
    await db_service.add_words([_DOM])
    assert "dom" in mock_backend._words.get("ru", {})
    assert any(lang == "ru" for _uid, _wid, lang in mock_backend._user_words)


# ---- DatabaseService.get_words ----


@pytest.mark.asyncio
async def test_get_words_returns_pairs(db_service: DatabaseService) -> None:
    """get_words returns WordPair list after translation completes."""
    await db_service.add_words([_HUIS])
    await asyncio.sleep(0.05)
    pairs = await db_service.get_words()
    assert len(pairs) == 1
    assert isinstance(pairs[0], WordPair)
    assert pairs[0].source.normalized_form == "huis"
    assert pairs[0].target.normalized_form == "HUIS"


@pytest.mark.asyncio
async def test_get_words_with_word_type(db_service: DatabaseService) -> None:
    """get_words filters by word_type."""
    await db_service.add_words([_HUIS, _LOPEN])
    await asyncio.sleep(0.05)
    pairs = await db_service.get_words(word_type=PartOfSpeech.NOUN)
    assert len(pairs) == 1
    assert pairs[0].source.word_type == PartOfSpeech.NOUN


@pytest.mark.asyncio
async def test_get_words_with_limit(db_service: DatabaseService) -> None:
    """get_words respects limit."""
    await db_service.add_words([_HUIS, _LOPEN, _SNEL])
    await asyncio.sleep(0.05)
    pairs = await db_service.get_words(limit=2)
    assert len(pairs) == 2


# ---- DatabaseService constructor ----


def test_constructor_raises_without_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """ConfigurationError raised when DATABASE_URL not set."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ConfigurationError):
        DatabaseService(user_id="u1")


# ---- CachedDatabaseService ----


@pytest.mark.asyncio
async def test_cached_service_caches_results(cached_service: CachedDatabaseService) -> None:
    """Second get_words call returns cached result without backend call."""
    await cached_service.add_words([_HUIS])
    await asyncio.sleep(0.05)
    first = await cached_service.get_words()
    second = await cached_service.get_words()
    assert first == second


@pytest.mark.asyncio
async def test_cached_service_clears_on_add(cached_service: CachedDatabaseService) -> None:
    """add_words clears the cache."""
    await cached_service.add_words([_HUIS])
    await asyncio.sleep(0.05)
    await cached_service.get_words()
    assert len(cached_service._cache) == 1
    await cached_service.add_words([_LOPEN])
    assert len(cached_service._cache) == 0


@pytest.mark.asyncio
async def test_cached_service_no_cache_random(cached_service: CachedDatabaseService) -> None:
    """random=True queries bypass cache."""
    await cached_service.add_words([_HUIS])
    await asyncio.sleep(0.05)
    await cached_service.get_words(random=True)
    assert len(cached_service._cache) == 0
