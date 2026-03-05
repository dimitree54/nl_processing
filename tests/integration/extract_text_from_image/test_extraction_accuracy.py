import pathlib
import time

import cv2
import pytest

from nl_processing.core.exceptions import TargetLanguageNotFoundError
from nl_processing.core.models import Language
from nl_processing.extract_text_from_image.benchmark import (
    evaluate_extraction,
    generate_test_image,
)
from nl_processing.extract_text_from_image.service import ImageTextExtractor


@pytest.mark.asyncio
async def test_simple_dutch_text_extraction(tmp_path: pathlib.Path) -> None:
    """Single line of simple Dutch text — baseline accuracy test."""
    ground_truth = "Het regent vandaag in Utrecht"
    image_path = str(tmp_path / "simple.png")
    generate_test_image(ground_truth, image_path, font_scale=1.5, width=900, height=100)

    extractor = ImageTextExtractor(language=Language.NL)
    extracted = await extractor.extract_from_path(image_path)

    assert evaluate_extraction(extracted, ground_truth), (
        f"Extraction mismatch.\nExpected: {ground_truth}\nGot: {extracted}"
    )


@pytest.mark.asyncio
async def test_multi_line_dutch_text_extraction(tmp_path: pathlib.Path) -> None:
    """Multi-line Dutch text — tests line break handling."""
    ground_truth = "Dit is een test\nvan meerdere regels"
    image_path = str(tmp_path / "multiline.png")
    generate_test_image(ground_truth, image_path, font_scale=1.2, width=800, height=200)

    extractor = ImageTextExtractor(language=Language.NL)
    extracted = await extractor.extract_from_path(image_path)

    assert evaluate_extraction(extracted, ground_truth), (
        f"Extraction mismatch.\nExpected: {ground_truth}\nGot: {extracted}"
    )


@pytest.mark.asyncio
async def test_extraction_from_cv2_array(tmp_path: pathlib.Path) -> None:
    """Test extract_from_cv2 produces same result as extract_from_path."""
    ground_truth = "Hallo wereld"
    image_path = str(tmp_path / "cv2test.png")
    generate_test_image(ground_truth, image_path, font_scale=1.5, width=600, height=100)

    cv2_image = cv2.imread(image_path)
    assert cv2_image is not None, f"Failed to load image from {image_path}"

    extractor = ImageTextExtractor(language=Language.NL)
    extracted = await extractor.extract_from_cv2(cv2_image)

    assert evaluate_extraction(extracted, ground_truth), (
        f"CV2 extraction mismatch.\nExpected: {ground_truth}\nGot: {extracted}"
    )


@pytest.mark.asyncio
async def test_extraction_latency(tmp_path: pathlib.Path) -> None:
    """Each extraction call completes in < 10 seconds (ETI-NFR1)."""
    ground_truth = "Snel test"
    image_path = str(tmp_path / "latency.png")
    generate_test_image(ground_truth, image_path, font_scale=1.5, width=400, height=100)

    extractor = ImageTextExtractor(language=Language.NL)
    start = time.time()
    await extractor.extract_from_path(image_path)
    elapsed = time.time() - start

    # NOTE: This is an integration test making a real API call; network latency is included.
    assert elapsed < 10, f"Extraction took {elapsed:.2f}s — exceeds 10.00s QA gate"


@pytest.mark.asyncio
async def test_mixed_dutch_russian_extracts_only_dutch(tmp_path: pathlib.Path) -> None:
    """Image with mixed Dutch + Russian text — only Dutch text should be extracted (FR3, FR4)."""
    dutch_text = "Goede reis"
    # Russian text renders as garbled chars in cv2, but the model should recognize
    # it as non-Dutch content and exclude it from extraction.
    mixed_text = f"{dutch_text}\nСчастливого пути"
    image_path = str(tmp_path / "mixed_lang.png")
    generate_test_image(mixed_text, image_path, font_scale=1.2, width=800, height=200)

    extractor = ImageTextExtractor(language=Language.NL)
    extracted = await extractor.extract_from_path(image_path)

    assert evaluate_extraction(extracted, dutch_text), (
        f"Mixed-language extraction failed.\nExpected (Dutch only): {dutch_text}\nGot: {extracted}"
    )


@pytest.mark.asyncio
async def test_english_only_raises_target_language_not_found(
    tmp_path: pathlib.Path,
) -> None:
    """Image with English-only text — should raise TargetLanguageNotFoundError (FR7).

    The LLM is non-deterministic and may occasionally return text for an
    English-only image even when configured for Dutch.  We retry up to 3
    times so that a single spurious LLM response does not cause a false
    failure.
    """
    english_text = "Remember to bring your umbrella tomorrow"
    image_path = str(tmp_path / "english_only.png")
    generate_test_image(english_text, image_path, font_scale=1.2, width=800, height=100)

    extractor = ImageTextExtractor(language=Language.NL)

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            await extractor.extract_from_path(image_path)
        except TargetLanguageNotFoundError:
            return  # expected error was raised — test passes
        if attempt == max_attempts:
            pytest.fail(f"TargetLanguageNotFoundError was not raised after {max_attempts} attempts")
