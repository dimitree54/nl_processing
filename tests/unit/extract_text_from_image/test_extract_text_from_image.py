import os
import pathlib
from types import SimpleNamespace
from unittest.mock import AsyncMock

import numpy as np
import pytest

from nl_processing.core.models import Language
from nl_processing.extract_text_from_image.benchmark import generate_test_image
from nl_processing.extract_text_from_image.service import ImageTextExtractor


def _make_tool_response(text: str) -> SimpleNamespace:
    """Build a fake LLM response with tool_calls matching bind_tools output."""
    resp = SimpleNamespace()
    resp.tool_calls = [{"args": {"text": text}}]
    return resp


def test_constructor_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test ImageTextExtractor constructor with default arguments."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    extractor = ImageTextExtractor()
    assert extractor._language == Language.NL
    # Chain should be stored (not prompt + llm separately)
    assert hasattr(extractor, "_chain")


def test_constructor_custom_params(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test ImageTextExtractor constructor with custom arguments."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    extractor = ImageTextExtractor(language=Language.NL, model="custom-model", reasoning_effort="high")
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
    extractor._chain = AsyncMock()
    extractor._chain.ainvoke = AsyncMock(return_value=_make_tool_response(expected_text))

    result = await extractor.extract_from_path(test_image_path)
    assert result == expected_text

    # Verify ainvoke was called with the right structure
    call_args = extractor._chain.ainvoke.call_args[0][0]
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
    extractor._chain = AsyncMock()
    extractor._chain.ainvoke = AsyncMock(return_value=_make_tool_response(expected_text))

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
    extractor._chain = AsyncMock()
    extractor._chain.ainvoke = AsyncMock(return_value=_make_tool_response("test result"))

    await extractor.extract_from_path(test_image_path)
    await extractor.extract_from_cv2(img)

    # Verify chain.ainvoke was called twice (once per method)
    assert extractor._chain.ainvoke.call_count == 2

    # Both calls should pass {"images": [HumanMessage(...)]}
    for call in extractor._chain.ainvoke.call_args_list:
        call_input = call[0][0]
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
    extractor._chain = AsyncMock()
    extractor._chain.ainvoke = AsyncMock(return_value=_make_tool_response(expected_text))

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
