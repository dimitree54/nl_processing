import numpy as np
import pytest

from nl_processing.core.exceptions import UnsupportedImageFormatError
from nl_processing.extract_text_from_image.benchmark import generate_test_image
from nl_processing.extract_text_from_image.image_encoding import (
    encode_cv2_to_base64,
    encode_path_to_base64,
    get_image_format,
    validate_image_format,
)


def test_get_image_format():
    """Test get_image_format returns lowercase extensions."""
    assert get_image_format("image.png") == ".png"
    assert get_image_format("image.jpg") == ".jpg"
    assert get_image_format("image.JPEG") == ".jpeg"
    assert get_image_format("image.gif") == ".gif"
    assert get_image_format("image.webp") == ".webp"
    assert get_image_format("image") == ""
    assert get_image_format("path/to/image.PNG") == ".png"


def test_encode_path_to_base64(tmp_path):
    """Test encoding image file to base64."""
    # Create a test image file
    test_image_path = str(tmp_path / "test.png")
    generate_test_image("Test", test_image_path)

    # Encode it
    base64_string, media_type = encode_path_to_base64(test_image_path)

    # Verify results
    assert isinstance(base64_string, str)
    assert len(base64_string) > 0
    assert media_type == "image/png"
    # Check it looks like base64
    import base64

    base64.b64decode(base64_string)  # Should not raise


def test_encode_cv2_to_base64():
    """Test encoding cv2 array to base64 PNG."""
    # Create a small white image array
    img = np.zeros((50, 100, 3), dtype=np.uint8)
    img.fill(255)

    # Encode it
    base64_string, media_type = encode_cv2_to_base64(img)

    # Verify results
    assert isinstance(base64_string, str)
    assert len(base64_string) > 0
    assert media_type == "image/png"
    # Check it looks like base64
    import base64

    base64.b64decode(base64_string)  # Should not raise


def test_validate_image_format_valid():
    """Test validate_image_format with valid formats."""
    valid_formats = [
        "image.png",
        "image.jpg",
        "image.jpeg",
        "image.gif",
        "image.webp",
        "path/to/image.PNG",  # uppercase should work
        "image.JPG",
    ]

    for image_path in valid_formats:
        validate_image_format(image_path)  # Should not raise


def test_validate_image_format_invalid():
    """Test validate_image_format with invalid formats."""
    invalid_formats = [
        "image.bmp",
        "image.tiff",
        "image.svg",
        "image",  # no extension
        "image.txt",
        "image.pdf",
    ]

    for image_path in invalid_formats:
        with pytest.raises(UnsupportedImageFormatError) as exc_info:
            validate_image_format(image_path)
        assert "Unsupported image format" in str(exc_info.value)


def test_encode_cv2_to_base64_failure():
    """Test encode_cv2_to_base64 with invalid array."""
    # Create an invalid array that might cause cv2.imencode to fail
    # This is difficult to trigger reliably, so we'll test with an empty array
    img = np.array([])

    # OpenCV throws cv2.error, not ValueError, for empty arrays
    import cv2

    with pytest.raises(cv2.error):
        encode_cv2_to_base64(img)


def test_encode_path_to_base64_file_not_found():
    """Test encode_path_to_base64 with non-existent file."""
    with pytest.raises(FileNotFoundError):
        encode_path_to_base64("nonexistent.png")
