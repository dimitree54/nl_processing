"""Basic tests for DetailedWordCacheService."""

from nl_processing.core.models import Language, PartOfSpeech, Word
import pytest

from nl_processing.database_cache.detailed_cache import DetailedWordCacheService


@pytest.mark.asyncio
async def test_get_or_fetch_details_empty_list() -> None:
    """Test that empty word list returns empty result."""
    service = DetailedWordCacheService(Language.NL, Language.RU)

    result = await service.get_or_fetch_details([])

    assert result == []


@pytest.mark.asyncio
async def test_missing_remote_store_on_cache_miss() -> None:
    """Test that missing remote store raises ValueError on cache miss."""
    from nl_processing.database_cache._detailed_local_store import DetailedLocalStore  # noqa: PLC0415

    local_store = DetailedLocalStore(":memory:")

    service = DetailedWordCacheService(
        Language.NL,
        Language.RU,
        remote_store=None,  # No remote store
        local_store=local_store,
    )

    words = [Word(normalized_form="missing", word_type=PartOfSpeech.NOUN, language=Language.NL)]

    with pytest.raises(ValueError, match="No remote store available for cache misses"):
        await service.get_or_fetch_details(words)
