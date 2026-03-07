"""Unit tests for DatabaseService."""

import asyncio

import pytest

from nl_processing.core.models import Language, PartOfSpeech, Word
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


@pytest.mark.asyncio
async def test_get_words_logs_warning_for_missing_translations(
    db_service: DatabaseService,
    mock_backend: MockBackend,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """get_words warns when untranslated user words are excluded."""
    await db_service.add_words([_HUIS])
    untranslated_id = await mock_backend.add_word("nl", "fiets", PartOfSpeech.NOUN.value)
    assert untranslated_id is not None
    await mock_backend.add_user_word("u1", untranslated_id, "nl")
    await asyncio.sleep(0.05)

    with caplog.at_level("WARNING", logger="nl_processing.database.service"):
        pairs = await db_service.get_words()

    assert len(pairs) == 1
    assert "1 of 2 words excluded from get_words() due to missing translations" in caplog.text
    assert mock_backend.count_user_words_calls == 1


@pytest.mark.asyncio
async def test_get_words_no_warning_when_all_words_are_translated(
    db_service: DatabaseService,
    mock_backend: MockBackend,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """get_words stays quiet when all user words have translations."""
    await db_service.add_words([_HUIS, _LOPEN])
    await asyncio.sleep(0.05)

    with caplog.at_level("WARNING", logger="nl_processing.database.service"):
        pairs = await db_service.get_words()

    assert len(pairs) == 2
    assert "excluded from get_words()" not in caplog.text
    assert mock_backend.count_user_words_calls == 1


@pytest.mark.asyncio
async def test_get_words_skips_count_when_limit_or_random(
    db_service: DatabaseService,
    mock_backend: MockBackend,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """get_words skips untranslated comparison for partial or random reads."""
    await db_service.add_words([_HUIS, _LOPEN])
    await asyncio.sleep(0.05)

    with caplog.at_level("WARNING", logger="nl_processing.database.service"):
        await db_service.get_words(limit=1)
        await db_service.get_words(random=True)

    assert "excluded from get_words()" not in caplog.text
    assert mock_backend.count_user_words_calls == 0


# ---- DatabaseService constructor ----


def test_constructor_raises_without_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """ConfigurationError raised when DATABASE_URL not set."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ConfigurationError):
        DatabaseService(user_id="u1")
