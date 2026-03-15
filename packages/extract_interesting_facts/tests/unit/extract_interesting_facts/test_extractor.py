from nl_processing.core.models import Language
import pytest

from nl_processing.extract_interesting_facts.service import InterestingFactsExtractor
from tests.unit.extract_interesting_facts.conftest import _AsyncChainMock, _make_text_response


def test_constructor_valid_pair_nl_ru(monkeypatch: pytest.MonkeyPatch) -> None:
    """NL→RU constructor succeeds and stores languages and chain."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    extractor = InterestingFactsExtractor(source_language=Language.NL, target_language=Language.RU)
    assert extractor._chain is not None
    assert extractor._source_language == Language.NL
    assert extractor._target_language == Language.RU


def test_constructor_unsupported_pair_nl_nl(monkeypatch: pytest.MonkeyPatch) -> None:
    """Same language raises ValueError with unsupported pair message."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    with pytest.raises(ValueError, match="Unsupported language pair nl->nl"):
        InterestingFactsExtractor(source_language=Language.NL, target_language=Language.NL)


def test_constructor_unsupported_pair_ru_nl(monkeypatch: pytest.MonkeyPatch) -> None:
    """RU→NL raises ValueError (only NL→RU is supported)."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    with pytest.raises(ValueError, match="Unsupported language pair ru->nl"):
        InterestingFactsExtractor(source_language=Language.RU, target_language=Language.NL)


def test_constructor_custom_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """Custom model and service_tier overrides are accepted."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    extractor = InterestingFactsExtractor(
        source_language=Language.NL,
        target_language=Language.RU,
        model="gpt-4o",
        service_tier="default",
    )
    assert extractor._chain is not None


def test_constructor_default_model_and_tier(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default model is gpt-4.1-mini and service_tier is priority."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    captured: dict[str, object] = {}

    def _fake_build_llm_kwargs(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"model": kwargs["model"]}

    monkeypatch.setattr(
        "nl_processing.extract_interesting_facts.service.build_llm_kwargs",
        _fake_build_llm_kwargs,
    )
    InterestingFactsExtractor(source_language=Language.NL, target_language=Language.RU)
    assert captured["model"] == "gpt-4.1-mini"
    assert captured["service_tier"] == "priority"


@pytest.mark.asyncio
async def test_extract_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valid Dutch text returns mocked response content."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    expected = "«Hond» — существительное мужского рода."
    extractor = InterestingFactsExtractor(source_language=Language.NL, target_language=Language.RU)
    extractor._chain = _AsyncChainMock(_make_text_response(expected))
    result = await extractor.extract("hond")
    assert result == expected


@pytest.mark.asyncio
async def test_extract_invokes_chain_with_correct_structure(monkeypatch: pytest.MonkeyPatch) -> None:
    """ainvoke is called once with correct HumanMessage structure."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    extractor = InterestingFactsExtractor(source_language=Language.NL, target_language=Language.RU)
    mock_chain = _AsyncChainMock(_make_text_response("Some analysis"))
    extractor._chain = mock_chain
    await extractor.extract("test text")
    assert len(mock_chain.ainvoke_calls) == 1
    call_args = mock_chain.ainvoke_calls[0]
    assert "text" in call_args
    assert len(call_args["text"]) == 1
