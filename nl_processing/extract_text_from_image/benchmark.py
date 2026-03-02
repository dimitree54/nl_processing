import re

import cv2
import numpy

from nl_processing.core.models import Language
from nl_processing.extract_text_from_image.service import ImageTextExtractor


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


def run_benchmark(
    test_cases: list[tuple[str, str]],
    *,
    model: str = "gpt-5-mini",
    language: Language = Language.NL,
) -> list[dict[str, str | bool]]:
    """Run the benchmark suite against a specified model.

    Args:
        test_cases: List of (image_path, ground_truth_text) tuples.
        model: LLM model name.
        language: Target language.

    Returns:
        List of result dicts with keys: image_path, ground_truth, extracted, passed.
    """
    extractor = ImageTextExtractor(language=language, model=model)
    results: list[dict[str, str | bool]] = []
    for image_path, ground_truth in test_cases:
        extracted = extractor.extract_from_path(image_path)
        passed = evaluate_extraction(extracted, ground_truth)
        results.append({
            "image_path": image_path,
            "ground_truth": ground_truth,
            "extracted": extracted,
            "passed": passed,
        })
    return results
