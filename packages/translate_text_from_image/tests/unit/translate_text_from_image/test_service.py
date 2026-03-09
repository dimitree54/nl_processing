import pathlib

import cv2
from nl_processing.core.models import Language
import numpy
import pytest

from nl_processing.translate_text_from_image.service import ImageTextTranslator
from tests.unit.translate_text_from_image.conftest import _AsyncChainMock, make_tool_response


def test_constructor_creates_chain_for_nl_ru(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test ImageTextTranslator constructor with NL->RU creates a working instance."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")

    translator = ImageTextTranslator(source_language=Language.NL, target_language=Language.RU)

    assert translator._source_language == Language.NL
    assert translator._target_language == Language.RU
    assert translator._chain is not None


def test_constructor_rejects_unsupported_pair(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test ImageTextTranslator raises ValueError for unsupported pair RU->NL."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")

    with pytest.raises(ValueError, match="Unsupported language pair"):
        ImageTextTranslator(source_language=Language.RU, target_language=Language.NL)


def test_constructor_accepts_all_optional_kwargs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test ImageTextTranslator constructor accepts model, reasoning_effort, service_tier, temperature."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")

    translator = ImageTextTranslator(
        source_language=Language.NL,
        target_language=Language.RU,
        model="gpt-4o-mini",
        reasoning_effort="high",
        service_tier="default",
        temperature=0.2,
    )

    assert translator._chain is not None


@pytest.mark.asyncio
async def test_translate_from_path_returns_translated_text(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """Test translate_from_path with mocked chain returns Russian translation."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")

    # Create test PNG image
    image_file = tmp_path / "sample.png"
    test_image = numpy.full((80, 300, 3), 255, dtype=numpy.uint8)
    cv2.imwrite(str(image_file), test_image)

    translated_text = "Кот сидит на коврике"

    translator = ImageTextTranslator(source_language=Language.NL, target_language=Language.RU)
    translator._chain = _AsyncChainMock(make_tool_response(translated_text))

    result = await translator.translate_from_path(str(image_file))

    assert result == translated_text


@pytest.mark.asyncio
async def test_translate_from_cv2_returns_translated_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test translate_from_cv2 with mocked chain returns Russian translation."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")

    # Create numpy image array directly
    image_array = numpy.zeros((120, 400, 3), dtype=numpy.uint8)
    image_array[:, :] = [240, 240, 240]  # Light gray background

    translated_text = "Добро пожаловать в мир"

    translator = ImageTextTranslator(source_language=Language.NL, target_language=Language.RU)
    translator._chain = _AsyncChainMock(make_tool_response(translated_text))

    result = await translator.translate_from_cv2(image_array)

    assert result == translated_text


@pytest.mark.asyncio
async def test_both_entrypoints_converge_to_single_chain(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """Test both translate_from_path and translate_from_cv2 call the same internal chain."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")

    # Create test PNG image file
    image_file = tmp_path / "test_image.png"
    file_image = numpy.full((100, 200, 3), 200, dtype=numpy.uint8)
    cv2.imwrite(str(image_file), file_image)

    # Create numpy array image
    array_image = numpy.full((100, 200, 3), 150, dtype=numpy.uint8)

    translator = ImageTextTranslator(source_language=Language.NL, target_language=Language.RU)
    mock_chain = _AsyncChainMock(make_tool_response("Тестовый результат"))
    translator._chain = mock_chain

    # Call both methods
    await translator.translate_from_path(str(image_file))
    await translator.translate_from_cv2(array_image)

    # Verify both calls went through the same chain
    assert len(mock_chain.ainvoke_calls) == 2

    # Both calls should have images parameter with HumanMessage
    first_call_args = mock_chain.ainvoke_calls[0]
    second_call_args = mock_chain.ainvoke_calls[1]

    assert "images" in first_call_args
    assert "images" in second_call_args
    assert len(first_call_args["images"]) == 1
    assert len(second_call_args["images"]) == 1


@pytest.mark.asyncio
async def test_exactly_one_chain_invocation_per_request(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """Test each translate call results in exactly one ainvoke call."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")

    # Create test image
    image_file = tmp_path / "single_call.png"
    img_data = numpy.full((60, 150, 3), 128, dtype=numpy.uint8)
    cv2.imwrite(str(image_file), img_data)

    translator = ImageTextTranslator(source_language=Language.NL, target_language=Language.RU)
    mock_chain = _AsyncChainMock(make_tool_response("Один вызов"))
    translator._chain = mock_chain

    # First translate call
    await translator.translate_from_path(str(image_file))
    assert len(mock_chain.ainvoke_calls) == 1, "First call should result in exactly 1 ainvoke"

    # Second translate call
    await translator.translate_from_path(str(image_file))
    assert len(mock_chain.ainvoke_calls) == 2, "Second call should result in exactly 1 additional ainvoke"

    # Each call should have the expected structure
    for call_input in mock_chain.ainvoke_calls:
        assert "images" in call_input
        assert len(call_input["images"]) == 1
