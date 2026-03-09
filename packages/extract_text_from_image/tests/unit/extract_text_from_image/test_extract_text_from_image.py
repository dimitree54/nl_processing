import os
import pathlib

from nl_processing.core.models import Language
import numpy as np
import pytest

from nl_processing.extract_text_from_image.benchmark import generate_test_image
from nl_processing.extract_text_from_image.service import ImageTextExtractor
from tests.unit.extract_text_from_image.conftest import _AsyncChainMock, make_tool_response


def test_constructor_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test ImageTextExtractor constructor with default arguments."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    extractor = ImageTextExtractor()
    assert extractor._language == Language.NL
    # Chain should be stored (not prompt + llm separately)
    assert extractor._chain is not None


def test_constructor_uses_offline_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default constructor should use the offline extraction profile."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    captured: dict[str, object] = {}

    class _PromptStub:
        def __or__(self, other: object) -> object:
            return other

    class _ChatStub:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

        def bind_tools(self, *_args: object, **_kwargs: object) -> "_ChatStub":
            return self

    monkeypatch.setattr("nl_processing.extract_text_from_image.service.load_prompt", lambda _path: _PromptStub())
    monkeypatch.setattr("nl_processing.extract_text_from_image.service.ChatOpenAI", _ChatStub)
    ImageTextExtractor()

    assert captured == {"model": "gpt-5-mini", "service_tier": None, "reasoning_effort": "medium", "temperature": None}


def test_constructor_custom_params(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test ImageTextExtractor constructor with custom arguments."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    extractor = ImageTextExtractor(
        language=Language.NL,
        model="custom-model",
        reasoning_effort="high",
        service_tier="flex",
        temperature=0.1,
    )
    assert extractor._language == Language.NL


def test_constructor_reasoning_effort_param(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test ImageTextExtractor constructor accepts reasoning_effort parameter."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    # Test None (default)
    extractor1 = ImageTextExtractor(reasoning_effort=None)
    assert extractor1._language == Language.NL

    # Test explicit values
    extractor2 = ImageTextExtractor(reasoning_effort="medium")
    assert extractor2._language == Language.NL


@pytest.mark.asyncio
async def test_extract_from_path_happy_path(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    """Test extract_from_path with mocked chain returning expected text."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    # Create a test image
    test_image_path = str(tmp_path / "test.png")
    generate_test_image("De kat zit op de mat", test_image_path)

    expected_text = "De kat zit op de mat"

    extractor = ImageTextExtractor()
    extractor._chain = _AsyncChainMock(make_tool_response(expected_text))

    result = await extractor.extract_from_path(test_image_path)
    assert result == expected_text

    # Verify ainvoke was called with the right structure
    call_args = extractor._chain.ainvoke_calls[0]
    assert "images" in call_args
    assert len(call_args["images"]) == 1


@pytest.mark.asyncio
async def test_extract_from_cv2_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test extract_from_cv2 with mocked chain returning expected text."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    img = np.zeros((100, 200, 3), dtype=np.uint8)
    img.fill(255)

    expected_text = "Hallo wereld"

    extractor = ImageTextExtractor()
    extractor._chain = _AsyncChainMock(make_tool_response(expected_text))

    result = await extractor.extract_from_cv2(img)
    assert result == expected_text


@pytest.mark.asyncio
async def test_both_methods_converge_to_chain(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    """Test that both extract_from_path and extract_from_cv2 invoke the same chain."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    # Create a test image
    test_image_path = str(tmp_path / "test.png")
    generate_test_image("Test", test_image_path)

    # Create a test image array
    img = np.zeros((50, 100, 3), dtype=np.uint8)
    img.fill(255)

    extractor = ImageTextExtractor()
    extractor._chain = _AsyncChainMock(make_tool_response("test result"))

    await extractor.extract_from_path(test_image_path)
    await extractor.extract_from_cv2(img)

    # Verify chain.ainvoke was called twice (once per method)
    assert len(extractor._chain.ainvoke_calls) == 2

    # Both calls should pass {"images": [HumanMessage(...)]}
    for call_input in extractor._chain.ainvoke_calls:
        assert "images" in call_input
        assert len(call_input["images"]) == 1


@pytest.mark.asyncio
async def test_extract_handles_tool_calls_response(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    """Test that _aextract handles tool_calls response from bind_tools."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    test_image_path = str(tmp_path / "test.png")
    generate_test_image("Test", test_image_path)

    expected_text = "Dit is een test"

    extractor = ImageTextExtractor()
    extractor._chain = _AsyncChainMock(make_tool_response(expected_text))

    result = await extractor.extract_from_path(test_image_path)
    assert result == expected_text


def test_extract_with_russian_language(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that constructor works with different language."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    # This will fail because we don't have ru.json prompt, but tests constructor logic
    with pytest.raises(FileNotFoundError):
        ImageTextExtractor(language=Language.RU)


def test_missing_openai_key() -> None:
    """Test that missing OPENAI_API_KEY raises appropriate error."""
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]

    with pytest.raises(Exception, match="api_key"):
        ImageTextExtractor()
