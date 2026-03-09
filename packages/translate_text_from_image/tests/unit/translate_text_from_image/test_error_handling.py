import pathlib

import cv2
from nl_processing.core.exceptions import APIError, TargetLanguageNotFoundError, UnsupportedImageFormatError
from nl_processing.core.models import Language
import numpy
import pytest

from nl_processing.translate_text_from_image.service import ImageTextTranslator
from tests.unit.translate_text_from_image.conftest import _AsyncChainMock, _AsyncChainMockError, make_tool_response


@pytest.mark.asyncio
async def test_bmp_format_rejected_before_chain_call(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    """Test UnsupportedImageFormatError for .bmp files is raised before chain invocation."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")

    # Create a BMP file (unsupported format)
    bmp_file_path = tmp_path / "unsupported_image.bmp"
    bmp_file_path.write_bytes(b"fake bmp data")

    translator = ImageTextTranslator(source_language=Language.NL, target_language=Language.RU)
    mock_chain = _AsyncChainMock(make_tool_response("Should not be reached"))
    translator._chain = mock_chain

    with pytest.raises(UnsupportedImageFormatError, match="Unsupported image format '.bmp'"):
        await translator.translate_from_path(str(bmp_file_path))

    # Chain should never be called for unsupported formats
    assert len(mock_chain.ainvoke_calls) == 0


@pytest.mark.asyncio
async def test_empty_translation_triggers_language_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """Test empty text from chain raises TargetLanguageNotFoundError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")

    # Create valid PNG image
    png_file = tmp_path / "valid_image.png"
    image_data = numpy.full((70, 120, 3), 220, dtype=numpy.uint8)
    cv2.imwrite(str(png_file), image_data)

    translator = ImageTextTranslator(source_language=Language.NL, target_language=Language.RU)
    # Mock chain returns empty string
    translator._chain = _AsyncChainMock(make_tool_response(""))

    with pytest.raises(TargetLanguageNotFoundError, match="No text in the source language was found in the image"):
        await translator.translate_from_path(str(png_file))


@pytest.mark.asyncio
async def test_whitespace_only_translation_triggers_language_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """Test whitespace-only text from chain raises TargetLanguageNotFoundError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")

    # Create valid PNG image
    png_file = tmp_path / "whitespace_result.png"
    img_array = numpy.full((90, 180, 3), 250, dtype=numpy.uint8)
    cv2.imwrite(str(png_file), img_array)

    translator = ImageTextTranslator(source_language=Language.NL, target_language=Language.RU)
    # Mock chain returns only whitespace
    translator._chain = _AsyncChainMock(make_tool_response("   \n\t   "))

    with pytest.raises(TargetLanguageNotFoundError, match="No text in the source language was found in the image"):
        await translator.translate_from_path(str(png_file))


@pytest.mark.asyncio
async def test_chain_runtime_error_wrapped_as_api_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """Test RuntimeError from chain is wrapped as APIError with original as __cause__."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")

    # Create valid PNG image
    png_file = tmp_path / "runtime_error.png"
    test_img = numpy.full((50, 100, 3), 180, dtype=numpy.uint8)
    cv2.imwrite(str(png_file), test_img)

    original_error = RuntimeError("Simulated chain failure")

    translator = ImageTextTranslator(source_language=Language.NL, target_language=Language.RU)
    translator._chain = _AsyncChainMockError(original_error)

    with pytest.raises(APIError) as exc_info:
        await translator.translate_from_path(str(png_file))

    # Verify the original error is preserved as __cause__
    assert exc_info.value.__cause__ is original_error
    assert str(exc_info.value) == "Simulated chain failure"


@pytest.mark.asyncio
async def test_chain_errors_all_wrapped_as_api_error(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    """Test various chain exception types are all wrapped as APIError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")

    # Create valid PNG image
    png_file = tmp_path / "multiple_errors.png"
    img_content = numpy.full((80, 160, 3), 160, dtype=numpy.uint8)
    cv2.imwrite(str(png_file), img_content)

    test_exceptions = [
        ValueError("Chain value error"),
        KeyError("Chain key error"),
        ConnectionError("Chain connection error"),
        TimeoutError("Chain timeout error"),
    ]

    translator = ImageTextTranslator(source_language=Language.NL, target_language=Language.RU)

    for original_exception in test_exceptions:
        translator._chain = _AsyncChainMockError(original_exception)

        with pytest.raises(APIError) as exc_info:
            await translator.translate_from_path(str(png_file))

        # Each should be wrapped with original preserved
        assert exc_info.value.__cause__ is original_exception


@pytest.mark.asyncio
async def test_cv2_entrypoint_also_wraps_chain_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test errors from cv2 entrypoint are also wrapped as APIError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")

    # Create numpy image array
    cv2_image = numpy.zeros((110, 220, 3), dtype=numpy.uint8)
    cv2_image.fill(190)

    original_exception = ConnectionError("CV2 path chain failure")

    translator = ImageTextTranslator(source_language=Language.NL, target_language=Language.RU)
    translator._chain = _AsyncChainMockError(original_exception)

    with pytest.raises(APIError) as exc_info:
        await translator.translate_from_cv2(cv2_image)

    # Error should be wrapped same way as path-based entrypoint
    assert exc_info.value.__cause__ is original_exception
    assert str(exc_info.value) == "CV2 path chain failure"
