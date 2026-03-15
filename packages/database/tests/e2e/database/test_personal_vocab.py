"""E2E tests for personal vocabulary with full translation flow."""

from datetime import datetime
import uuid

from nl_processing.core.models import Language, PartOfSpeech, Word
import pytest

from nl_processing.database.backend.neon import NeonBackend
from tests.e2e.database.conftest import make_service, wait_for_translations


@pytest.mark.asyncio
async def test_list_personal_words_e2e(db_ready: NeonBackend) -> None:
    """E2E test: add words with translator, wait for translations, call list_personal_words."""
    user_id = f"test-user-{uuid.uuid4()}"
    service = make_service(user_id, backend=db_ready)

    unique_id = uuid.uuid4().hex[:8]
    dutch_words = [
        Word(normalized_form=f"huis_{unique_id}", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form=f"boom_{unique_id}", word_type=PartOfSpeech.NOUN, language=Language.NL),
    ]

    result = await service.add_words(dutch_words)
    assert len(result.new_words) == 2

    await wait_for_translations(expected_count=2, backend=db_ready)

    personal_words = await service.list_personal_words(exercise_types=["flashcard"])

    assert len(personal_words) == 2

    for personal_word in personal_words:
        assert personal_word.pair.source.language == Language.NL
        assert personal_word.pair.target.language == Language.RU
        assert isinstance(personal_word.source_word_id, int)
        assert isinstance(personal_word.target_word_id, int)
        assert isinstance(personal_word.added_at, datetime)
        assert personal_word.scores == {"flashcard": 0}

    source_words = [pw.pair.source.normalized_form for pw in personal_words]
    assert f"huis_{unique_id}" in source_words
    assert f"boom_{unique_id}" in source_words
