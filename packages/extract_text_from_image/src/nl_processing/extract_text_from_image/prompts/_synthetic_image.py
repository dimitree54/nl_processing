from pathlib import Path

import cv2
import numpy


def generate_test_image(
    text: str,
    output_path: str,
    *,
    width: int = 800,
    height: int = 200,
    font_scale: float = 1.0,
    thickness: int = 2,
) -> str:
    """Generate a synthetic image with rendered text."""
    image = numpy.zeros((height, width, 3), dtype=numpy.uint8)
    image.fill(255)

    y_offset = 40
    line_height = int(40 * font_scale)
    for line in text.split("\n"):
        cv2.putText(image, line, (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness)
        y_offset += line_height

    if not cv2.imwrite(output_path, image):
        raise ValueError(f"Failed to write image to {output_path}")
    return str(Path(output_path))
