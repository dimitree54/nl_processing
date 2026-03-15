import pathlib
import time
from typing import Coroutine

import cv2
from nl_processing.core.exceptions import TargetLanguageNotFoundError
from nl_processing.core.models import Language
import pytest

from nl_processing.extract_text_from_image.prompts._synthetic_image import generate_test_image
from nl_processing.extract_text_from_image.service import ImageTextExtractor
from tests.helpers.text_comparison import evaluate_extraction


async def _extract_with_latency_assertion(coro: Coroutine[object, object, str]) -> str:
    start = time.perf_counter()
    result = await coro
    elapsed = time.perf_counter() - start
    assert elapsed < 20, f"Extraction took {elapsed:.2f}s - exceeds 20.00s QA gate"
    return result


@pytest.mark.asyncio
async def test_simple_dutch_text_extraction(tmp_path: pathlib.Path) -> None:
    """Single line of simple Dutch text — baseline accuracy test."""
    ground_truth = "Het regent vandaag in Utrecht"
    image_path = str(tmp_path / "simple.png")
    generate_test_image(ground_truth, image_path, font_scale=1.5, width=900, height=100)

    extractor = ImageTextExtractor(language=Language.NL)
    extracted = await _extract_with_latency_assertion(extractor.extract_from_path(image_path))

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
    extracted = await _extract_with_latency_assertion(extractor.extract_from_cv2(cv2_image))

    assert evaluate_extraction(extracted, ground_truth), (
        f"CV2 extraction mismatch.\nExpected: {ground_truth}\nGot: {extracted}"
    )


@pytest.mark.asyncio
async def test_english_only_raises_target_language_not_found(
    tmp_path: pathlib.Path,
) -> None:
    """Image with English-only text should raise TargetLanguageNotFoundError (FR5)."""
    english_text = "Remember to charge your phone before leaving tomorrow"
    image_path = str(tmp_path / "english_only.png")
    generate_test_image(english_text, image_path, font_scale=1.2, width=800, height=100)

    extractor = ImageTextExtractor(language=Language.NL)

    with pytest.raises(TargetLanguageNotFoundError):
        await extractor.extract_from_path(image_path)
