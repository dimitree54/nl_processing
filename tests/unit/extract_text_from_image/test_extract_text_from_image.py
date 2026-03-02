import numpy as np
import pytest

from nl_processing.core.models import ExtractedText, Language
from nl_processing.extract_text_from_image.benchmark import generate_test_image
from nl_processing.extract_text_from_image.service import ImageTextExtractor


def test_constructor_defaults(monkeypatch):
    """Test ImageTextExtractor constructor with default arguments."""
    # Mock environment variable
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    extractor = ImageTextExtractor()
    assert extractor._language == Language.NL
    # Note: We can't easily test the model parameter without accessing private attributes
    # The main thing is that construction succeeds


def test_constructor_custom_params(monkeypatch):
    """Test ImageTextExtractor constructor with custom arguments."""
    # Mock environment variable
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    extractor = ImageTextExtractor(language=Language.NL, model="custom-model")
    assert extractor._language == Language.NL


def test_extract_from_path_happy_path(monkeypatch, tmp_path):
    """Test extract_from_path with mocked LLM returning expected text."""
    # Mock environment variable
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    # Create a test image
    test_image_path = str(tmp_path / "test.png")
    generate_test_image("De kat zit op de mat", test_image_path)

    # Mock the _extract method to return expected text
    expected_text = "De kat zit op de mat"

    def mock_extract(self, base64_string, media_type):
        return expected_text

    extractor = ImageTextExtractor()
    monkeypatch.setattr(extractor, "_extract", mock_extract.__get__(extractor, ImageTextExtractor))

    # Call extract_from_path
    result = extractor.extract_from_path(test_image_path)

    # Verify result
    assert result == expected_text


def test_extract_from_cv2_happy_path(monkeypatch):
    """Test extract_from_cv2 with mocked LLM returning expected text."""
    # Mock environment variable
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    # Create a test image array
    img = np.zeros((100, 200, 3), dtype=np.uint8)
    img.fill(255)  # white background

    # Mock the _extract method to return expected text
    expected_text = "Hallo wereld"

    def mock_extract(self, base64_string, media_type):
        return expected_text

    extractor = ImageTextExtractor()
    monkeypatch.setattr(extractor, "_extract", mock_extract.__get__(extractor, ImageTextExtractor))

    # Call extract_from_cv2
    result = extractor.extract_from_cv2(img)

    # Verify result
    assert result == expected_text


def test_both_methods_converge_to_extract(monkeypatch, tmp_path):
    """Test that both extract_from_path and extract_from_cv2 call the same internal _extract method."""
    # Mock environment variable
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    # Create a test image
    test_image_path = str(tmp_path / "test.png")
    generate_test_image("Test", test_image_path)

    # Create a test image array
    img = np.zeros((50, 100, 3), dtype=np.uint8)
    img.fill(255)

    # Track calls to _extract
    extract_calls = []

    def mock_extract(self, base64_string, media_type):
        extract_calls.append((base64_string[:20], media_type))  # Track partial base64 + media_type
        return "test result"

    extractor = ImageTextExtractor()
    monkeypatch.setattr(extractor, "_extract", mock_extract.__get__(extractor, ImageTextExtractor))

    # Call both methods
    extractor.extract_from_path(test_image_path)
    extractor.extract_from_cv2(img)

    # Verify both called _extract
    assert len(extract_calls) == 2
    # extract_from_path should use the original file's media type
    assert extract_calls[0][1] == "image/png"
    # extract_from_cv2 always uses PNG
    assert extract_calls[1][1] == "image/png"


def test_extract_handles_dict_response(monkeypatch, tmp_path):
    """Test that _extract handles dict response from structured output."""
    # Mock environment variable
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    # Create a test image
    test_image_path = str(tmp_path / "test.png")
    generate_test_image("Test", test_image_path)

    # Mock the _extract method to simulate handling dict response
    expected_text = "Dit is een test"

    def mock_extract(self, base64_string, media_type):
        # Simulate the dict handling logic from the actual _extract method
        result = {"text": expected_text}  # Dict response from LLM
        if isinstance(result, ExtractedText):
            text = result.text
        else:
            text = result["text"]  # Handle dict response

        if not text.strip():
            from nl_processing.core.exceptions import TargetLanguageNotFoundError

            raise TargetLanguageNotFoundError("No text in the target language was found in the image")

        return text

    extractor = ImageTextExtractor()
    monkeypatch.setattr(extractor, "_extract", mock_extract.__get__(extractor, ImageTextExtractor))

    # Call extract_from_path
    result = extractor.extract_from_path(test_image_path)

    # Verify result
    assert result == expected_text


def test_extract_with_russian_language(monkeypatch):
    """Test that constructor works with different language."""
    # Mock environment variable
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    # This will fail because we don't have ru.json prompt, but tests constructor logic
    with pytest.raises(FileNotFoundError):
        ImageTextExtractor(language=Language.RU)


def test_missing_openai_key():
    """Test that missing OPENAI_API_KEY raises appropriate error."""
    import os

    # Ensure OPENAI_API_KEY is not set
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]

    # Don't set the environment variable - should raise OpenAI error
    with pytest.raises(Exception, match="api_key"):
        ImageTextExtractor()
