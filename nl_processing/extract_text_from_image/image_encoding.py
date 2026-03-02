import base64
import pathlib

import cv2
import numpy

from nl_processing.core.exceptions import UnsupportedImageFormatError

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def get_image_format(path: str) -> str:
    """Return the file extension (lowercase) for the given image path."""
    return pathlib.Path(path).suffix.lower()


def validate_image_format(path: str) -> None:
    """Validate that the image format is supported by OpenAI Vision API.

    Raises:
        UnsupportedImageFormatError: If the file extension is not in SUPPORTED_EXTENSIONS.
    """
    suffix = get_image_format(path)
    if suffix not in SUPPORTED_EXTENSIONS:
        msg = f"Unsupported image format '{suffix}'. Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        raise UnsupportedImageFormatError(msg)


def encode_path_to_base64(path: str) -> tuple[str, str]:
    """Read an image file and return (base64_string, media_type).

    Does NOT validate format — caller is responsible for validation.
    """
    suffix = get_image_format(path)
    media_type = _suffix_to_media_type(suffix)
    with open(path, "rb") as f:
        image_bytes = f.read()
    base64_string = base64.b64encode(image_bytes).decode("utf-8")
    return base64_string, media_type


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
