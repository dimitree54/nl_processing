import base64
from pathlib import Path

import cv2
import numpy
import pytest

from nl_processing.core.exceptions import UnsupportedImageFormatError
from nl_processing.core.image_encoding import (
    SUPPORTED_EXTENSIONS,
    build_image_human_message,
    encode_cv2_to_base64,
    encode_image_path,
    encode_path_to_base64,
    validate_image_format,
)


def _create_tiny_png(path: Path) -> Path:
    """Create a minimal 1x1 red PNG image file."""
    image = numpy.zeros((1, 1, 3), dtype=numpy.uint8)
    image[0, 0] = (0, 0, 255)  # BGR red
    cv2.imwrite(str(path), image)
    return path


def test_validate_image_format_accepts_supported() -> None:
    """Test validate_image_format accepts all supported extensions."""
    for ext in SUPPORTED_EXTENSIONS:
        validate_image_format(f"image{ext}")


def test_validate_image_format_normalizes_suffix_case() -> None:
    """Test validate_image_format accepts supported extensions with mixed case."""
    validate_image_format("photo.PNG")
    validate_image_format("photo.JpG")
    validate_image_format("/some/path/image.jpeg")


def test_validate_image_format_rejects_unsupported() -> None:
    """Test validate_image_format raises UnsupportedImageFormatError for unsupported formats."""
    with pytest.raises(UnsupportedImageFormatError, match="Unsupported image format '.bmp'"):
        validate_image_format("photo.bmp")


def test_validate_image_format_rejects_no_extension() -> None:
    """Test validate_image_format raises UnsupportedImageFormatError for files without extension."""
    with pytest.raises(UnsupportedImageFormatError):
        validate_image_format("no_extension")


def test_encode_path_to_base64_returns_valid_base64(tmp_path: Path) -> None:
    """Test encode_path_to_base64 returns decodable base64 and correct media type."""
    png_path = _create_tiny_png(tmp_path / "test.png")

    base64_str, media_type = encode_path_to_base64(str(png_path))

    assert media_type == "image/png"
    decoded = base64.b64decode(base64_str)
    assert len(decoded) > 0


def test_encode_path_to_base64_round_trips_file_content(tmp_path: Path) -> None:
    """Test encode_path_to_base64 round-trips the exact file bytes."""
    png_path = _create_tiny_png(tmp_path / "test.png")
    original_bytes = png_path.read_bytes()

    base64_str, _media_type = encode_path_to_base64(str(png_path))

    assert base64.b64decode(base64_str) == original_bytes


def test_encode_image_path_matches_encode_path_to_base64(tmp_path: Path) -> None:
    """Test encode_image_path is the public path helper for image-file encoding."""
    png_path = _create_tiny_png(tmp_path / "test.png")

    assert encode_image_path(str(png_path)) == encode_path_to_base64(str(png_path))


def test_encode_path_to_base64_jpeg_media_type(tmp_path: Path) -> None:
    """Test encode_path_to_base64 returns image/jpeg for .jpg files."""
    jpg_path = tmp_path / "test.jpg"
    image = numpy.zeros((1, 1, 3), dtype=numpy.uint8)
    cv2.imwrite(str(jpg_path), image)

    _base64_str, media_type = encode_path_to_base64(str(jpg_path))

    assert media_type == "image/jpeg"


def test_encode_path_to_base64_maps_other_media_types(tmp_path: Path) -> None:
    """Test encode_path_to_base64 maps supported non-JPEG suffixes correctly."""
    gif_path = tmp_path / "photo.GIF"
    gif_path.write_bytes(b"gif-bytes")

    _base64_str, media_type = encode_path_to_base64(str(gif_path))

    assert media_type == "image/gif"


def test_encode_cv2_to_base64_returns_png() -> None:
    """Test encode_cv2_to_base64 returns base64 PNG with correct media type."""
    image = numpy.zeros((2, 2, 3), dtype=numpy.uint8)

    base64_str, media_type = encode_cv2_to_base64(image)

    assert media_type == "image/png"
    decoded = base64.b64decode(base64_str)
    assert decoded[:4] == b"\x89PNG"


def test_build_image_human_message_uses_data_url_payload() -> None:
    """Test build_image_human_message wraps image bytes in one data URL block."""
    message = build_image_human_message("YWJj", "image/png")

    assert message.content == [
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,YWJj"}},
    ]


def test_encode_cv2_to_base64_preserves_pixel_data() -> None:
    """Test encode_cv2_to_base64 produces an image decodable back to original pixels."""
    original = numpy.array([[[255, 0, 0], [0, 255, 0]]], dtype=numpy.uint8)

    base64_str, _media_type = encode_cv2_to_base64(original)

    decoded_bytes = base64.b64decode(base64_str)
    decoded_array = numpy.frombuffer(decoded_bytes, dtype=numpy.uint8)
    decoded_image = cv2.imdecode(decoded_array, cv2.IMREAD_COLOR)
    numpy.testing.assert_array_equal(decoded_image, original)


def test_encode_cv2_to_base64_handles_imencode_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test encode_cv2_to_base64 raises ValueError when OpenCV encoding fails."""

    def _fail_imencode(_extension: str, _image: numpy.ndarray) -> tuple[bool, numpy.ndarray]:
        return False, numpy.array([], dtype=numpy.uint8)

    monkeypatch.setattr(cv2, "imencode", _fail_imencode)

    image = numpy.zeros((1, 1, 3), dtype=numpy.uint8)

    with pytest.raises(ValueError, match="Failed to encode image to PNG"):
        encode_cv2_to_base64(image)


def test_supported_extensions_contains_expected_formats() -> None:
    """Test SUPPORTED_EXTENSIONS contains exactly the expected formats."""
    assert SUPPORTED_EXTENSIONS == {".png", ".jpg", ".jpeg", ".gif", ".webp"}
