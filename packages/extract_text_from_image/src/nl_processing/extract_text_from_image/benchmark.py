import re

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
    """Generate a synthetic test image with known text rendered on it.

    Returns the output file path.
    """
    img = numpy.zeros((height, width, 3), dtype=numpy.uint8)
    img.fill(255)  # white background

    lines = text.split("\n")
    y_offset = 40
    line_height = int(40 * font_scale)

    for line in lines:
        cv2.putText(
            img,
            line,
            (20, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (0, 0, 0),
            thickness,
        )
        y_offset += line_height

    success = cv2.imwrite(output_path, img)
    if not success:
        raise ValueError(f"Failed to write image to {output_path}")
    return output_path


def normalize_text(text: str) -> str:
    """Normalize text for comparison: strip whitespace, line breaks, markdown formatting."""
    normalized = re.sub(r"[#*_~`>\-]+", "", text)  # remove markdown chars
    normalized = re.sub(r"\s+", " ", normalized)  # collapse whitespace
    return normalized.strip().lower()


def evaluate_extraction(extracted: str, ground_truth: str) -> bool:
    """Compare extracted text against ground truth after normalization.

    Returns True if exact match after normalization.
    """
    return normalize_text(extracted) == normalize_text(ground_truth)
