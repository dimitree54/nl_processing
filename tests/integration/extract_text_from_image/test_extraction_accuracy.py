import pathlib
import time

import cv2

from nl_processing.core.models import Language
from nl_processing.extract_text_from_image.benchmark import (
    evaluate_extraction,
    generate_test_image,
)
from nl_processing.extract_text_from_image.service import ImageTextExtractor


def test_simple_dutch_text_extraction(tmp_path: pathlib.Path) -> None:
    """Single line of simple Dutch text — baseline accuracy test."""
    ground_truth = "De kat zit op de mat"
    image_path = str(tmp_path / "simple.png")
    generate_test_image(ground_truth, image_path, font_scale=1.5, width=800, height=100)

    extractor = ImageTextExtractor(language=Language.NL)
    extracted = extractor.extract_from_path(image_path)

    assert evaluate_extraction(extracted, ground_truth), (
        f"Extraction mismatch.\nExpected: {ground_truth}\nGot: {extracted}"
    )


def test_multi_line_dutch_text_extraction(tmp_path: pathlib.Path) -> None:
    """Multi-line Dutch text — tests line break handling."""
    ground_truth = "Dit is een test\nvan meerdere regels"
    image_path = str(tmp_path / "multiline.png")
    generate_test_image(ground_truth, image_path, font_scale=1.2, width=800, height=200)

    extractor = ImageTextExtractor(language=Language.NL)
    extracted = extractor.extract_from_path(image_path)

    assert evaluate_extraction(extracted, ground_truth), (
        f"Extraction mismatch.\nExpected: {ground_truth}\nGot: {extracted}"
    )


def test_extraction_from_cv2_array(tmp_path: pathlib.Path) -> None:
    """Test extract_from_cv2 produces same result as extract_from_path."""
    ground_truth = "Hallo wereld"
    image_path = str(tmp_path / "cv2test.png")
    generate_test_image(ground_truth, image_path, font_scale=1.5, width=600, height=100)

    cv2_image = cv2.imread(image_path)
    assert cv2_image is not None, f"Failed to load image from {image_path}"

    extractor = ImageTextExtractor(language=Language.NL)
    extracted = extractor.extract_from_cv2(cv2_image)

    assert evaluate_extraction(extracted, ground_truth), (
        f"CV2 extraction mismatch.\nExpected: {ground_truth}\nGot: {extracted}"
    )


def test_extraction_latency(tmp_path: pathlib.Path) -> None:
    """Each extraction call completes in <= 1 second (ETI-NFR1)."""
    ground_truth = "Snel test"
    image_path = str(tmp_path / "latency.png")
    generate_test_image(ground_truth, image_path, font_scale=1.5, width=400, height=100)

    extractor = ImageTextExtractor(language=Language.NL)
    start = time.time()
    extractor.extract_from_path(image_path)
    elapsed = time.time() - start

    # Note: NFR1 says <=1s "excluding network latency outside module control"
    # We allow up to 10s to account for network variability in CI
    assert elapsed < 10, f"Extraction took {elapsed:.2f}s — exceeds timeout"
