"""E2e tests for untranslated word exclusion: get_words uses INNER JOIN."""

from uuid import uuid4

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database_core.backend.neon import NeonBackend
import pytest

from tests.e2e.database.conftest import cleanup_service, make_service

_WORDS = [
    Word(normalized_form="appel", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="melk", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="brood", word_type=PartOfSpeech.NOUN, language=Language.NL),
]


@pytest.mark.asyncio
async def test_untranslated_words_excluded_immediately(db_ready: NeonBackend) -> None:
    """Immediately after add_words, get_words excludes untranslated words."""
    user_id = f"e2e_user_{uuid4()}"
    service = make_service(user_id, backend=db_ready)

    await service.add_words(_WORDS)
    pairs = await service.get_words()

    assert len(pairs) < len(_WORDS) or len(pairs) == 0


@pytest.mark.asyncio
async def test_translated_words_included_after_wait(db_ready: NeonBackend) -> None:
    """After translations complete, get_words returns all word pairs."""
    user_id = f"e2e_user_{uuid4()}"
    service = make_service(user_id, backend=db_ready)

    await service.add_words(_WORDS)
    # Wait for background translations and surface any failures
    await cleanup_service(service)

    pairs = await service.get_words()
    assert len(pairs) == len(_WORDS)

    source_forms = {p.source.normalized_form for p in pairs}
    for word in _WORDS:
        assert word.normalized_form in source_forms
