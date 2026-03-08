"""E2e tests for user word lists: isolation, filtering, and random selection."""

from uuid import uuid4

from nl_processing.core.models import Language, PartOfSpeech, Word
import pytest

from nl_processing.database.testing import count_user_words
from tests.e2e.database.conftest import make_service, wait_for_translations

_NOUNS = [
    Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="boek", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="fiets", word_type=PartOfSpeech.NOUN, language=Language.NL),
]

_VERB = Word(normalized_form="lopen", word_type=PartOfSpeech.VERB, language=Language.NL)
_ALL_WORDS = [*_NOUNS, _VERB]


@pytest.mark.asyncio
@pytest.mark.usefixtures("db_ready")
async def test_user_word_isolation() -> None:
    """Words added by different users are isolated per user."""
    user_a = f"e2e_user_a_{uuid4()}"
    user_b = f"e2e_user_b_{uuid4()}"

    service_a = make_service(user_a)
    service_b = make_service(user_b)

    await service_a.add_words(_NOUNS)
    await service_b.add_words([_VERB])

    count_a = await count_user_words(user_a, "nl")
    count_b = await count_user_words(user_b, "nl")

    assert count_a == len(_NOUNS)
    assert count_b == 1


@pytest.mark.asyncio
@pytest.mark.usefixtures("db_ready")
async def test_get_words_filters_by_noun() -> None:
    """get_words with word_type=NOUN returns only nouns after translation."""
    user_id = f"e2e_user_{uuid4()}"
    service = make_service(user_id)

    await service.add_words(_ALL_WORDS)
    await wait_for_translations(len(_ALL_WORDS))

    noun_pairs = await service.get_words(word_type=PartOfSpeech.NOUN)
    assert len(noun_pairs) == len(_NOUNS)
    for pair in noun_pairs:
        assert pair.source.word_type == PartOfSpeech.NOUN


@pytest.mark.asyncio
@pytest.mark.usefixtures("db_ready")
async def test_get_words_random_returns_unique_pairs() -> None:
    """get_words with limit=3, random=True returns exactly 3 unique pairs."""
    user_id = f"e2e_user_{uuid4()}"
    service = make_service(user_id)

    await service.add_words(_ALL_WORDS)
    await wait_for_translations(len(_ALL_WORDS))

    pairs = await service.get_words(limit=3, random=True)
    assert len(pairs) == 3

    source_forms = {p.source.normalized_form for p in pairs}
    assert len(source_forms) == 3


@pytest.mark.asyncio
@pytest.mark.usefixtures("db_ready")
async def test_get_words_returns_all_translated() -> None:
    """get_words without filters returns all translated word pairs."""
    user_id = f"e2e_user_{uuid4()}"
    service = make_service(user_id)

    await service.add_words(_ALL_WORDS)
    await wait_for_translations(len(_ALL_WORDS))

    pairs = await service.get_words()
    assert len(pairs) == len(_ALL_WORDS)

    for pair in pairs:
        assert pair.source.language == Language.NL
        assert pair.target.language == Language.RU
        assert pair.target.normalized_form.strip()
