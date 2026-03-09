"""Synthetic image generation for prompt examples and tests."""

import cv2
import numpy


def render_text_image(
    text: str,
    output_path: str,
    *,
    image_width: int = 800,
    image_height: int = 200,
    scale: float = 1.0,
    line_thickness: int = 2,
) -> str:
    """Render text onto a white image and save to disk. Returns the path."""
    canvas = numpy.full((image_height, image_width, 3), 255, dtype=numpy.uint8)
    y_pos = 40
    spacing = int(40 * scale)

    for line in text.split("\n"):
        cv2.putText(canvas, line, (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), line_thickness)
        y_pos += spacing

    if not cv2.imwrite(output_path, canvas):
        msg = f"Failed to write image to {output_path}"
        raise ValueError(msg)
    return output_path
