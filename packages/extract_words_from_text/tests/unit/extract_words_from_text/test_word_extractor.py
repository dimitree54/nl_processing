from nl_processing.core.models import Language, PartOfSpeech, Word
import pytest

from nl_processing.extract_words_from_text.service import WordExtractor
from tests.unit.extract_words_from_text.conftest import _AsyncChainMock, make_tool_response


def test_constructor_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test WordExtractor constructor with default arguments."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    extractor = WordExtractor()
    assert extractor._language == Language.NL
    assert extractor._chain is not None


def test_constructor_custom_params(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test WordExtractor constructor with custom arguments."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    extractor = WordExtractor(language=Language.NL, model="custom-model")
    assert extractor._language == Language.NL


def test_constructor_missing_prompt_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that unsupported language raises FileNotFoundError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    with pytest.raises(FileNotFoundError):
        WordExtractor(language=Language.RU)


@pytest.mark.asyncio
async def test_extract_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test extract returns correct list of Word objects."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    words_data = [
        {"normalized_form": "de kat", "word_type": "noun"},
        {"normalized_form": "lopen", "word_type": "verb"},
    ]

    extractor = WordExtractor()
    extractor._chain = _AsyncChainMock(make_tool_response(words_data))

    result = await extractor.extract("De kat loopt.")
    assert len(result) == 2
    assert result[0].normalized_form == "de kat"
    assert result[0].word_type == PartOfSpeech.NOUN
    assert result[0].language == Language.NL
    assert result[1].normalized_form == "lopen"
    assert result[1].word_type == PartOfSpeech.VERB
    assert result[1].language == Language.NL


@pytest.mark.asyncio
async def test_extract_returns_word_objects(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that each returned item is a Word instance."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    words_data = [
        {"normalized_form": "de fiets", "word_type": "noun"},
        {"normalized_form": "groot", "word_type": "adjective"},
        {"normalized_form": "fietsen", "word_type": "verb"},
    ]

    extractor = WordExtractor()
    extractor._chain = _AsyncChainMock(make_tool_response(words_data))

    result = await extractor.extract("De grote fiets fietst.")
    assert all(isinstance(w, Word) for w in result)
    for w in result:
        assert w.normalized_form
        assert isinstance(w.word_type, PartOfSpeech)
        assert w.language == Language.NL


@pytest.mark.asyncio
async def test_extract_empty_list_for_non_target_language(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that extract returns empty list when LLM finds no target-language words."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    extractor = WordExtractor()
    extractor._chain = _AsyncChainMock(make_tool_response([]))

    result = await extractor.extract("The quick brown fox jumps.")
    assert result == []
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_extract_invokes_chain_with_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that ainvoke is called with the correct input structure."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    words_data = [{"normalized_form": "hallo", "word_type": "noun"}]
    mock = _AsyncChainMock(make_tool_response(words_data))

    extractor = WordExtractor()
    extractor._chain = mock

    await extractor.extract("Hallo wereld.")

    assert len(mock.ainvoke_calls) == 1
    call_args = mock.ainvoke_calls[0]
    assert "text" in call_args
    assert len(call_args["text"]) == 1
