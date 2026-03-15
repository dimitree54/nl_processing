"""E2e tests for word addition flow: add Dutch words, verify DB state, await translations."""

from uuid import uuid4

from nl_processing.core.models import Language, PartOfSpeech, Word
import pytest

from nl_processing.database.backend.neon import NeonBackend
from nl_processing.database.testing import count_translation_links, count_words
from tests.e2e.database.conftest import make_service, wait_for_translations

_DUTCH_WORDS = [
    Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="boek", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="fiets", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="school", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="water", word_type=PartOfSpeech.NOUN, language=Language.NL),
]


@pytest.mark.asyncio
async def test_add_words_inserts_into_database(db_ready: NeonBackend) -> None:
    """Adding a batch of Dutch words inserts them into words_nl."""
    user_id = f"e2e_user_{uuid4()}"
    service = make_service(user_id, backend=db_ready)
    await service.add_words(_DUTCH_WORDS)

    nl_count = await count_words("nl", backend=db_ready)
    assert nl_count >= len(_DUTCH_WORDS)


@pytest.mark.asyncio
async def test_add_words_reports_new_vs_existing(db_ready: NeonBackend) -> None:
    """First add reports all as new; second add reports all as existing."""
    user_id = f"e2e_user_{uuid4()}"
    service = make_service(user_id, backend=db_ready)

    first_result = await service.add_words(_DUTCH_WORDS)
    assert len(first_result.new_words) == len(_DUTCH_WORDS)
    assert len(first_result.existing_words) == 0

    second_result = await service.add_words(_DUTCH_WORDS)
    assert len(second_result.new_words) == 0
    assert len(second_result.existing_words) == len(_DUTCH_WORDS)


@pytest.mark.asyncio
async def test_add_words_no_duplicates_on_repeat(db_ready: NeonBackend) -> None:
    """Adding same words twice does not create duplicate rows in words_nl."""
    user_id = f"e2e_user_{uuid4()}"
    service = make_service(user_id, backend=db_ready)

    await service.add_words(_DUTCH_WORDS)
    count_after_first = await count_words("nl", backend=db_ready)

    await service.add_words(_DUTCH_WORDS)
    count_after_second = await count_words("nl", backend=db_ready)

    assert count_after_second == count_after_first


@pytest.mark.asyncio
async def test_translations_appear_after_add(db_ready: NeonBackend) -> None:
    """Fire-and-forget translation creates translation links within timeout."""
    user_id = f"e2e_user_{uuid4()}"
    service = make_service(user_id, backend=db_ready)

    links_before = await count_translation_links("nl_ru", backend=db_ready)
    await service.add_words(_DUTCH_WORDS)

    expected = links_before + len(_DUTCH_WORDS)
    await wait_for_translations(expected, backend=db_ready)

    links_after = await count_translation_links("nl_ru", backend=db_ready)
    assert links_after >= expected
