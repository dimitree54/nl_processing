import base64
import pathlib
import tempfile

import cv2
from langchain_core.messages import HumanMessage
import numpy

from nl_processing.core.exceptions import UnsupportedImageFormatError

_SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def _get_image_format(path: str) -> str:
    """Return the file extension (lowercase) for the given image path."""
    return pathlib.Path(path).suffix.lower()


def validate_image_format(path: str) -> None:
    """Validate that the image format is supported by OpenAI Vision API.

    Raises:
        UnsupportedImageFormatError: If the file extension is not in _SUPPORTED_EXTENSIONS.
    """
    suffix = _get_image_format(path)
    if suffix not in _SUPPORTED_EXTENSIONS:
        msg = f"Unsupported image format '{suffix}'. Supported formats: {', '.join(sorted(_SUPPORTED_EXTENSIONS))}"
        raise UnsupportedImageFormatError(msg)


def encode_path_to_base64(path: str) -> tuple[str, str]:
    """Read an image file and return (base64_string, media_type).

    Does NOT validate format — caller is responsible for validation.
    """
    suffix = _get_image_format(path)
    media_type = _suffix_to_media_type(suffix)
    with open(path, "rb") as f:
        image_bytes = f.read()
    base64_string = base64.b64encode(image_bytes).decode("utf-8")
    return base64_string, media_type


def encode_image_path(path: str) -> tuple[str, str]:
    """Read an image file path and return (base64_string, media_type)."""
    return encode_path_to_base64(path)


def encode_cv2_to_base64(image: numpy.ndarray) -> tuple[str, str]:
    """Encode an OpenCV image array to base64 PNG.

    Returns (base64_string, media_type).
    """
    success, buffer = cv2.imencode(".png", image)
    if not success:
        msg = "Failed to encode image to PNG"
        raise ValueError(msg)
    base64_string = base64.b64encode(buffer.tobytes()).decode("utf-8")
    return base64_string, "image/png"


def build_image_human_message(base64_string: str, media_type: str) -> HumanMessage:
    """Build a HumanMessage for one base64-encoded image payload."""
    image_url = f"data:{media_type};base64,{base64_string}"
    return HumanMessage(content=[{"type": "image_url", "image_url": {"url": image_url}}])


def generate_test_image(
    text: str,
    output_path: str,
    *,
    width: int = 800,
    height: int = 200,
    font_scale: float = 1.0,
    thickness: int = 2,
) -> str:
    """Generate a synthetic image with rendered text.

    Args:
        text: Text to render. Newlines will create separate lines.
        output_path: Path where to write the image file.
        width: Image width in pixels.
        height: Image height in pixels.
        font_scale: Font scaling factor.
        thickness: Line thickness for text.

    Returns:
        The written output path as a string.

    Raises:
        ValueError: If the image cannot be written.
    """
    image = numpy.zeros((height, width, 3), dtype=numpy.uint8)
    image.fill(255)  # White background

    y_offset = 40
    line_height = int(40 * font_scale)
    for line in text.split("\n"):
        cv2.putText(image, line, (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness)
        y_offset += line_height

    if not cv2.imwrite(output_path, image):
        raise ValueError(f"Failed to write image to {output_path}")
    return str(pathlib.Path(output_path))


def generate_test_image_data_url(
    text: str,
    *,
    width: int = 800,
    height: int = 200,
    font_scale: float = 1.2,
    thickness: int = 2,
) -> str:
    """Generate a synthetic image and return its base64 data URL.

    Args:
        text: Text to render. Newlines will create separate lines.
        width: Image width in pixels.
        height: Image height in pixels.
        font_scale: Font scaling factor.
        thickness: Line thickness for text.

    Returns:
        A complete data URL in format data:image/png;base64,<payload>

    Raises:
        ValueError: If the image cannot be generated or encoded.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = str(pathlib.Path(tmpdir) / "synthetic.png")
        generate_test_image(text, img_path, width=width, height=height, font_scale=font_scale, thickness=thickness)
        base64_string, media_type = encode_path_to_base64(img_path)
    return f"data:{media_type};base64,{base64_string}"


def _suffix_to_media_type(suffix: str) -> str:
    """Convert file extension to MIME media type."""
    mapping = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return mapping[suffix]
