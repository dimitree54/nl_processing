"""E2e smoke test for real OpenAI + real Neon translation orchestration."""

from uuid import uuid4

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database_core.backend.neon import NeonBackend
import pytest

from tests.e2e.database.conftest import cleanup_service, make_service

# Small set of words for smoke testing real translation orchestration
_SMOKE_WORDS = [
    Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="boek", word_type=PartOfSpeech.NOUN, language=Language.NL),
]


@pytest.mark.asyncio
async def test_end_to_end_translation_orchestration_smoke(db_ready: NeonBackend) -> None:
    """Smoke test: add_words with real translator + eventual translated get_words reads.

    This is the single E2E test that proves real OpenAI + real Neon translation
    orchestration from DatabaseService.add_words() to eventual translated reads.
    """
    user_id = f"e2e_smoke_user_{uuid4()}"
    service = make_service(user_id, backend=db_ready)

    # Add words with real translator orchestration
    result = await service.add_words(_SMOKE_WORDS)
    assert len(result.new_words) == len(_SMOKE_WORDS)

    # Wait for background translations to complete
    await cleanup_service(service)

    # Verify translated pairs are eventually readable
    pairs = await service.get_words()
    assert len(pairs) == len(_SMOKE_WORDS)

    # Verify we got real translations (not just seeded data)
    source_forms = {p.source.normalized_form for p in pairs}
    for word in _SMOKE_WORDS:
        assert word.normalized_form in source_forms

    # Verify translations have actual target content
    for pair in pairs:
        assert pair.source.language == Language.NL
        assert pair.target.language == Language.RU
        assert pair.target.normalized_form.strip()  # Non-empty Russian translation
