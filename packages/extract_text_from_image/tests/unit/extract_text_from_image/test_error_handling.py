import pathlib

from nl_processing.core.exceptions import (
    APIError,
    TargetLanguageNotFoundError,
    UnsupportedImageFormatError,
)
import numpy as np
import pytest

from nl_processing.extract_text_from_image.benchmark import generate_test_image
from nl_processing.extract_text_from_image.service import ImageTextExtractor
from tests.unit.extract_text_from_image.conftest import (
    _AsyncChainMock,
    _AsyncChainMockError,
    make_tool_response,
)


def _setup_extractor_with_mock_chain(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    mock_text_response: str,
) -> tuple[str, ImageTextExtractor]:
    """Helper: create extractor with chain mocked to return the given text."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    test_image_path = str(tmp_path / "test.png")
    generate_test_image("Test", test_image_path)

    extractor = ImageTextExtractor()
    extractor._chain = _AsyncChainMock(make_tool_response(mock_text_response))

    return test_image_path, extractor


@pytest.mark.asyncio
async def test_unsupported_format_in_extract_from_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that unsupported formats raise UnsupportedImageFormatError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    extractor = ImageTextExtractor()

    # Format validation happens before any chain invocation
    with pytest.raises(UnsupportedImageFormatError):
        await extractor.extract_from_path("test.bmp")


@pytest.mark.asyncio
async def test_target_language_not_found_empty_text(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    """Test that empty extracted text raises TargetLanguageNotFoundError."""
    test_image_path, extractor = _setup_extractor_with_mock_chain(monkeypatch, tmp_path, "")

    with pytest.raises(TargetLanguageNotFoundError, match="No text in the target language"):
        await extractor.extract_from_path(test_image_path)


@pytest.mark.asyncio
async def test_target_language_not_found_whitespace_text(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """Test that whitespace-only extracted text raises TargetLanguageNotFoundError."""
    test_image_path, extractor = _setup_extractor_with_mock_chain(monkeypatch, tmp_path, "   \n  \t  ")

    with pytest.raises(TargetLanguageNotFoundError, match="No text in the target language"):
        await extractor.extract_from_path(test_image_path)


@pytest.mark.asyncio
async def test_api_error_wrapping_runtime_error(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    """Test that RuntimeError from chain is wrapped as APIError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    test_image_path = str(tmp_path / "test.png")
    generate_test_image("Test", test_image_path)

    extractor = ImageTextExtractor()
    extractor._chain = _AsyncChainMockError(RuntimeError("API failed"))

    with pytest.raises(APIError) as exc_info:
        await extractor.extract_from_path(test_image_path)

    # Verify the original exception is preserved as __cause__
    assert exc_info.value.__cause__.__class__ == RuntimeError
    assert str(exc_info.value.__cause__) == "API failed"


@pytest.mark.asyncio
async def test_api_error_wrapping_various_exceptions(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    """Test that various exceptions from chain are wrapped as APIError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    test_image_path = str(tmp_path / "test.png")
    generate_test_image("Test", test_image_path)

    exceptions_to_test = [
        ValueError("Value error"),
        ConnectionError("Connection failed"),
        KeyError("Key error"),
        Exception("Generic exception"),
    ]

    extractor = ImageTextExtractor()

    for original_exception in exceptions_to_test:
        extractor._chain = _AsyncChainMockError(original_exception)

        with pytest.raises(APIError) as exc_info:
            await extractor.extract_from_path(test_image_path)

        # Verify the original exception is preserved
        assert exc_info.value.__cause__ is original_exception


@pytest.mark.asyncio
async def test_api_error_wrapping_cv2_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that API errors are wrapped for cv2 path too."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    img = np.zeros((50, 100, 3), dtype=np.uint8)
    img.fill(255)

    extractor = ImageTextExtractor()
    extractor._chain = _AsyncChainMockError(ValueError("API error in cv2 path"))

    with pytest.raises(APIError) as exc_info:
        await extractor.extract_from_cv2(img)

    assert exc_info.value.__cause__.__class__ == ValueError
    assert str(exc_info.value.__cause__) == "API error in cv2 path"
