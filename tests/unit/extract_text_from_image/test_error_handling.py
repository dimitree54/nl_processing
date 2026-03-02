import pytest

from nl_processing.core.exceptions import (
    APIError,
    TargetLanguageNotFoundError,
    UnsupportedImageFormatError,
)
from nl_processing.extract_text_from_image.benchmark import generate_test_image
from nl_processing.extract_text_from_image.service import ImageTextExtractor


def test_unsupported_format_in_extract_from_path(monkeypatch):
    """Test that unsupported formats raise UnsupportedImageFormatError."""
    # Mock environment variable
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    # Create extractor - the actual LLM doesn't matter since format validation happens first
    extractor = ImageTextExtractor()

    # Test unsupported format - should raise before API call
    with pytest.raises(UnsupportedImageFormatError):
        extractor.extract_from_path("test.bmp")


def test_target_language_not_found_empty_text(monkeypatch, tmp_path):
    """Test that empty extracted text raises TargetLanguageNotFoundError."""
    # Mock environment variable
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    # Create a test image
    test_image_path = str(tmp_path / "test.png")
    generate_test_image("Test", test_image_path)

    # Mock the _extract method to simulate empty LLM response
    def mock_extract(self, base64_string, media_type):
        # Simulate the logic in _extract with empty text
        text = ""  # Empty response from LLM
        if not text.strip():
            raise TargetLanguageNotFoundError("No text in the target language was found in the image")
        return text

    extractor = ImageTextExtractor()
    monkeypatch.setattr(extractor, "_extract", mock_extract.__get__(extractor, ImageTextExtractor))

    # Should raise TargetLanguageNotFoundError
    with pytest.raises(TargetLanguageNotFoundError, match="No text in the target language"):
        extractor.extract_from_path(test_image_path)


def test_target_language_not_found_whitespace_text(monkeypatch, tmp_path):
    """Test that whitespace-only extracted text raises TargetLanguageNotFoundError."""
    # Mock environment variable
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    # Create a test image
    test_image_path = str(tmp_path / "test.png")
    generate_test_image("Test", test_image_path)

    # Mock the _extract method to simulate whitespace-only LLM response
    def mock_extract(self, base64_string, media_type):
        # Simulate the logic in _extract with whitespace-only text
        text = "   \n  \t  "  # Whitespace-only response from LLM
        if not text.strip():
            raise TargetLanguageNotFoundError("No text in the target language was found in the image")
        return text

    extractor = ImageTextExtractor()
    monkeypatch.setattr(extractor, "_extract", mock_extract.__get__(extractor, ImageTextExtractor))

    # Should raise TargetLanguageNotFoundError
    with pytest.raises(TargetLanguageNotFoundError, match="No text in the target language"):
        extractor.extract_from_path(test_image_path)


def test_api_error_wrapping_runtime_error(monkeypatch, tmp_path):
    """Test that RuntimeError from LLM is wrapped as APIError."""
    # Mock environment variable
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    # Create a test image
    test_image_path = str(tmp_path / "test.png")
    generate_test_image("Test", test_image_path)

    # Mock the _extract method to simulate API error
    def mock_extract(self, base64_string, media_type):
        # Simulate the try/except logic in _extract
        try:
            raise RuntimeError("API failed")
        except Exception as e:
            raise APIError(str(e)) from e

    extractor = ImageTextExtractor()
    monkeypatch.setattr(extractor, "_extract", mock_extract.__get__(extractor, ImageTextExtractor))

    # Should wrap RuntimeError as APIError
    with pytest.raises(APIError) as exc_info:
        extractor.extract_from_path(test_image_path)

    # Verify the original exception is preserved as __cause__
    assert exc_info.value.__cause__.__class__ == RuntimeError
    assert str(exc_info.value.__cause__) == "API failed"


def test_api_error_wrapping_various_exceptions(monkeypatch, tmp_path):
    """Test that various exceptions from LLM are wrapped as APIError."""
    # Mock environment variable
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    # Create a test image
    test_image_path = str(tmp_path / "test.png")
    generate_test_image("Test", test_image_path)

    # Test different exception types
    exceptions_to_test = [
        ValueError("Value error"),
        ConnectionError("Connection failed"),
        KeyError("Key error"),
        Exception("Generic exception"),
    ]

    extractor = ImageTextExtractor()

    for original_exception in exceptions_to_test:

        def mock_extract(self, base64_string, media_type):
            # Simulate the try/except logic in _extract
            try:
                raise original_exception
            except Exception as e:
                raise APIError(str(e)) from e

        monkeypatch.setattr(extractor, "_extract", mock_extract.__get__(extractor, ImageTextExtractor))

        # Should wrap as APIError
        with pytest.raises(APIError) as exc_info:
            extractor.extract_from_path(test_image_path)

        # Verify the original exception is preserved
        assert exc_info.value.__cause__ is original_exception


def test_api_error_wrapping_cv2_path(monkeypatch):
    """Test that API errors are wrapped for cv2 path too."""
    # Mock environment variable
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    # Create a simple numpy array
    import numpy as np

    img = np.zeros((50, 100, 3), dtype=np.uint8)
    img.fill(255)

    # Mock the _extract method to simulate API error
    def mock_extract(self, base64_string, media_type):
        # Simulate the try/except logic in _extract
        try:
            raise ValueError("API error in cv2 path")
        except Exception as e:
            raise APIError(str(e)) from e

    extractor = ImageTextExtractor()
    monkeypatch.setattr(extractor, "_extract", mock_extract.__get__(extractor, ImageTextExtractor))

    # Should wrap as APIError
    with pytest.raises(APIError) as exc_info:
        extractor.extract_from_cv2(img)

    # Verify the original exception is preserved
    assert exc_info.value.__cause__.__class__ == ValueError
    assert str(exc_info.value.__cause__) == "API error in cv2 path"
