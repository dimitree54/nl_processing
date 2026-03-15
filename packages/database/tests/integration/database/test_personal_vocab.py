"""Integration tests for personal vocabulary against real Neon database."""

from datetime import datetime
import uuid

from nl_processing.core.models import Language, PartOfSpeech
from nl_processing.database_core.backend.neon import NeonBackend
import pytest

from nl_processing.database.service import DatabaseService


@pytest.mark.asyncio
async def test_list_personal_words_integration(neon_backend: NeonBackend) -> None:
    """Integration test: set up words, translations, user associations in real DB."""
    user_id = f"test-user-{uuid.uuid4()}"

    # Create service
    service = DatabaseService(user_id=user_id, backend=neon_backend)

    # Add a unique Dutch word
    unique_word = f"huis_{uuid.uuid4().hex[:8]}"
    word_id = await neon_backend.add_word("nl", unique_word, PartOfSpeech.NOUN.value)
    assert word_id is not None

    # Add unique Russian translation
    unique_translation = f"дом_{uuid.uuid4().hex[:8]}"
    target_id = await neon_backend.add_word("ru", unique_translation, PartOfSpeech.NOUN.value)
    assert target_id is not None

    # Link them
    await neon_backend.add_translation_link("nl_ru", word_id, target_id)

    # Associate with user
    await neon_backend.add_user_word(user_id, word_id, Language.NL.value)

    # Add some exercise scores
    await neon_backend.increment_user_exercise_score("nl_ru_flashcard", user_id, word_id, 3)

    # Call list_personal_words
    result = await service.list_personal_words(exercise_types=["flashcard"])

    assert len(result) == 1
    personal_word = result[0]
    assert personal_word.pair.source.normalized_form == unique_word
    assert personal_word.pair.target.normalized_form == unique_translation
    assert personal_word.source_word_id == word_id
    assert personal_word.target_word_id == target_id
    assert isinstance(personal_word.added_at, datetime)
    assert personal_word.scores == {"flashcard": 3}
