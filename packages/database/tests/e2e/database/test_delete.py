"""E2E tests for delete functionality."""

import uuid

from nl_processing.core.models import Language, PartOfSpeech, Word
import pytest

from nl_processing.database.backend.neon import NeonBackend
from nl_processing.database.exceptions import WordNotFoundError
from tests.e2e.database.conftest import make_service


@pytest.mark.asyncio
async def test_delete_word_e2e_flow(db_ready: NeonBackend) -> None:
    """Test end-to-end delete flow: add words, wait for translations, delete one."""
    user_id = f"test-user-{uuid.uuid4()}"
    service_with_translation = make_service(user_id, backend=db_ready)
    word_form = f"testword_{uuid.uuid4().hex[:8]}"

    word = Word(normalized_form=word_form, word_type=PartOfSpeech.NOUN, language=Language.NL)
    result = await service_with_translation.add_words([word])
    assert len(result.new_words) == 1

    backend = service_with_translation._backend

    word_dict = await backend.get_word("nl", word_form)
    source_word_id = int(word_dict["id"])

    target_word_id = await backend.add_word("ru", f"ru_{word_form}", "noun")
    if target_word_id is None:
        target_dict = await backend.get_word("ru", f"ru_{word_form}")
        target_word_id = int(target_dict["id"])

    await backend.add_translation_link("nl_ru", source_word_id, target_word_id)

    words = await service_with_translation.get_words()
    initial_count = len(words)
    assert initial_count > 0

    our_word = None
    for word_pair in words:
        if word_pair.source.normalized_form == word_form:
            our_word = word_pair
            break
    assert our_word is not None

    await service_with_translation.delete_word(source_word_id)

    words = await service_with_translation.get_words()
    final_count = len(words)
    assert final_count == initial_count - 1

    for word_pair in words:
        assert word_pair.source.normalized_form != word_form


@pytest.mark.asyncio
async def test_delete_nonexistent_word_raises_error(db_ready: NeonBackend) -> None:
    """Test that deleting a non-existent word raises WordNotFoundError."""
    user_id = f"test-user-{uuid.uuid4()}"
    service_with_translation = make_service(user_id, backend=db_ready)
    nonexistent_id = 999999

    with pytest.raises(WordNotFoundError) as exc_info:
        await service_with_translation.delete_word(nonexistent_id)

    assert "not in user's vocabulary" in str(exc_info.value)
    assert str(nonexistent_id) in str(exc_info.value)


@pytest.mark.asyncio
async def test_delete_multiple_words_e2e(db_ready: NeonBackend) -> None:
    """Test deleting multiple words at once."""
    user_id = f"test-user-{uuid.uuid4()}"
    service_with_translation = make_service(user_id, backend=db_ready)
    word_forms = [f"testword_{uuid.uuid4().hex[:8]}", f"testword_{uuid.uuid4().hex[:8]}"]

    words = [Word(normalized_form=form, word_type=PartOfSpeech.NOUN, language=Language.NL) for form in word_forms]
    result = await service_with_translation.add_words(words)
    assert len(result.new_words) == 2

    backend = service_with_translation._backend

    source_word_ids = []
    for word_form in word_forms:
        word_dict = await backend.get_word("nl", word_form)
        source_word_id = int(word_dict["id"])
        source_word_ids.append(source_word_id)

        target_word_id = await backend.add_word("ru", f"ru_{word_form}", "noun")
        if target_word_id is None:
            target_dict = await backend.get_word("ru", f"ru_{word_form}")
            target_word_id = int(target_dict["id"])

        await backend.add_translation_link("nl_ru", source_word_id, target_word_id)

    words_before = await service_with_translation.get_words()
    initial_count = len(words_before)

    our_words_count = 0
    for word_pair in words_before:
        if word_pair.source.normalized_form in word_forms:
            our_words_count += 1
    assert our_words_count == 2

    await service_with_translation.delete_words(source_word_ids)

    words_after = await service_with_translation.get_words()
    final_count = len(words_after)
    assert final_count == initial_count - 2

    for word_pair in words_after:
        assert word_pair.source.normalized_form not in word_forms


@pytest.mark.asyncio
async def test_delete_empty_list_noop(db_ready: NeonBackend) -> None:
    """Test that deleting empty list does nothing and doesn't error."""
    user_id = f"test-user-{uuid.uuid4()}"
    service_with_translation = make_service(user_id, backend=db_ready)
    words_before = await service_with_translation.get_words()

    await service_with_translation.delete_words([])

    words_after = await service_with_translation.get_words()
    assert len(words_after) == len(words_before)
