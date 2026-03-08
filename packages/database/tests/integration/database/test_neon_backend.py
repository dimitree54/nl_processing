"""Integration tests for NeonBackend CRUD operations against real Neon PostgreSQL."""

import uuid

import pytest

from nl_processing.database.backend.neon import NeonBackend


def _uid() -> str:
    """Generate a unique user_id to avoid pytest-xdist conflicts."""
    return f"test_user_{uuid.uuid4().hex[:12]}"


@pytest.mark.asyncio
async def test_add_word_inserts_and_returns_id(neon_backend: NeonBackend) -> None:
    """add_word inserts a new word and returns its integer id."""
    word_id = await neon_backend.add_word("nl", f"huis_{uuid.uuid4().hex[:8]}", "noun")
    assert word_id is not None
    assert isinstance(word_id, int)


@pytest.mark.asyncio
async def test_add_word_duplicate_returns_none(neon_backend: NeonBackend) -> None:
    """add_word for a duplicate normalized_form returns None."""
    unique_word = f"dubbel_{uuid.uuid4().hex[:8]}"
    first_id = await neon_backend.add_word("nl", unique_word, "noun")
    assert first_id is not None

    second_id = await neon_backend.add_word("nl", unique_word, "noun")
    assert second_id is None


@pytest.mark.asyncio
async def test_get_word_retrieves_inserted_word(neon_backend: NeonBackend) -> None:
    """get_word returns the correct word dict after insertion."""
    unique_word = f"boek_{uuid.uuid4().hex[:8]}"
    word_id = await neon_backend.add_word("nl", unique_word, "noun")

    result = await neon_backend.get_word("nl", unique_word)
    assert result is not None
    assert result["id"] == word_id
    assert result["normalized_form"] == unique_word
    assert result["word_type"] == "noun"


@pytest.mark.asyncio
async def test_get_word_nonexistent_returns_none(neon_backend: NeonBackend) -> None:
    """get_word for a non-existent word returns None."""
    result = await neon_backend.get_word("nl", f"nonexistent_{uuid.uuid4().hex[:8]}")
    assert result is None


@pytest.mark.asyncio
async def test_add_translation_link_creates_link(neon_backend: NeonBackend) -> None:
    """add_translation_link creates a translation link between source and target words."""
    src_word = f"water_{uuid.uuid4().hex[:8]}"
    tgt_word = f"вода_{uuid.uuid4().hex[:8]}"
    src_id = await neon_backend.add_word("nl", src_word, "noun")
    tgt_id = await neon_backend.add_word("ru", tgt_word, "noun")
    assert src_id is not None
    assert tgt_id is not None

    await neon_backend.add_translation_link("nl_ru", src_id, tgt_id)

    user_id = _uid()
    await neon_backend.add_user_word(user_id, src_id, "nl")
    rows = await neon_backend.get_user_words(user_id, "nl")
    source_forms = [str(r["source_normalized_form"]) for r in rows]
    assert src_word in source_forms


@pytest.mark.asyncio
async def test_add_user_word_creates_association(neon_backend: NeonBackend) -> None:
    """add_user_word creates a user-word association."""
    unique_word = f"fiets_{uuid.uuid4().hex[:8]}"
    word_id = await neon_backend.add_word("nl", unique_word, "noun")
    assert word_id is not None

    user_id = _uid()
    await neon_backend.add_user_word(user_id, word_id, "nl")

    tgt_word = f"велосипед_{uuid.uuid4().hex[:8]}"
    tgt_id = await neon_backend.add_word("ru", tgt_word, "noun")
    assert tgt_id is not None
    await neon_backend.add_translation_link("nl_ru", word_id, tgt_id)

    rows = await neon_backend.get_user_words(user_id, "nl")
    assert len(rows) >= 1
    source_forms = [str(r["source_normalized_form"]) for r in rows]
    assert unique_word in source_forms


@pytest.mark.asyncio
async def test_get_user_words_returns_correct_data(neon_backend: NeonBackend) -> None:
    """get_user_words returns correct translated word pairs for a user."""
    user_id = _uid()
    src1 = f"kat_{uuid.uuid4().hex[:8]}"
    tgt1 = f"кот_{uuid.uuid4().hex[:8]}"
    src2 = f"hond_{uuid.uuid4().hex[:8]}"
    tgt2 = f"собака_{uuid.uuid4().hex[:8]}"

    s1_id = await neon_backend.add_word("nl", src1, "noun")
    t1_id = await neon_backend.add_word("ru", tgt1, "noun")
    s2_id = await neon_backend.add_word("nl", src2, "noun")
    t2_id = await neon_backend.add_word("ru", tgt2, "noun")
    assert all(i is not None for i in [s1_id, t1_id, s2_id, t2_id])

    await neon_backend.add_translation_link("nl_ru", s1_id, t1_id)
    await neon_backend.add_translation_link("nl_ru", s2_id, t2_id)
    await neon_backend.add_user_word(user_id, s1_id, "nl")
    await neon_backend.add_user_word(user_id, s2_id, "nl")

    rows = await neon_backend.get_user_words(user_id, "nl")
    source_forms = {str(r["source_normalized_form"]) for r in rows}
    assert src1 in source_forms
    assert src2 in source_forms


@pytest.mark.asyncio
async def test_get_user_words_with_word_type_filter(neon_backend: NeonBackend) -> None:
    """get_user_words filters by word_type."""
    user_id = _uid()
    noun_src = f"boom_{uuid.uuid4().hex[:8]}"
    verb_src = f"lopen_{uuid.uuid4().hex[:8]}"
    noun_tgt = f"дерево_{uuid.uuid4().hex[:8]}"
    verb_tgt = f"ходить_{uuid.uuid4().hex[:8]}"

    n_id = await neon_backend.add_word("nl", noun_src, "noun")
    v_id = await neon_backend.add_word("nl", verb_src, "verb")
    nt_id = await neon_backend.add_word("ru", noun_tgt, "noun")
    vt_id = await neon_backend.add_word("ru", verb_tgt, "verb")

    await neon_backend.add_translation_link("nl_ru", n_id, nt_id)
    await neon_backend.add_translation_link("nl_ru", v_id, vt_id)
    await neon_backend.add_user_word(user_id, n_id, "nl")
    await neon_backend.add_user_word(user_id, v_id, "nl")

    noun_rows = await neon_backend.get_user_words(user_id, "nl", word_type="noun")
    for row in noun_rows:
        assert row["source_word_type"] == "noun"

    verb_rows = await neon_backend.get_user_words(user_id, "nl", word_type="verb")
    for row in verb_rows:
        assert row["source_word_type"] == "verb"


@pytest.mark.asyncio
async def test_get_user_words_with_limit(neon_backend: NeonBackend) -> None:
    """get_user_words respects the limit parameter."""
    user_id = _uid()
    for i in range(5):
        src = f"woord_{i}_{uuid.uuid4().hex[:8]}"
        tgt = f"слово_{i}_{uuid.uuid4().hex[:8]}"
        s_id = await neon_backend.add_word("nl", src, "noun")
        t_id = await neon_backend.add_word("ru", tgt, "noun")
        await neon_backend.add_translation_link("nl_ru", s_id, t_id)
        await neon_backend.add_user_word(user_id, s_id, "nl")

    rows = await neon_backend.get_user_words(user_id, "nl", limit=3)
    assert len(rows) == 3
