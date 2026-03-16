"""Regression tests for background task failure cleanup behavior."""

import asyncio
from typing import Protocol

from nl_processing.core.models import Language, PartOfSpeech, Word
import pytest

from nl_processing.database.service import DatabaseService
from tests.unit.database.mock_backend import MockBackend


class Translator(Protocol):
    """Protocol for translator objects used in tests."""

    async def translate(self, words: list[Word]) -> list[Word]:
        """Translate words."""
        ...


class FailingTranslator:
    """Mock translator that always fails and tracks call count."""

    def __init__(self) -> None:
        self.call_count = 0

    async def translate(self, words: list[Word]) -> list[Word]:  # noqa: ARG002
        self.call_count += 1
        raise RuntimeError("Translation service unavailable")


class SuccessfulTranslator:
    """Mock translator that always succeeds and tracks call count."""

    def __init__(self) -> None:
        self.call_count = 0

    async def translate(self, words: list[Word]) -> list[Word]:
        self.call_count += 1
        return [Word(normalized_form="тест", word_type=PartOfSpeech.NOUN, language=Language.RU) for _ in words]


def _create_service(translator: Translator | None) -> DatabaseService:
    """Helper to create database service with given translator."""
    backend = MockBackend()
    return DatabaseService(
        user_id="test_user",
        source_language=Language.NL,
        target_language=Language.RU,
        backend=backend,
        translator=translator,
    )


async def _add_test_words(service: DatabaseService) -> None:
    """Helper to add test words that trigger background translation."""
    words = [Word(normalized_form="test", word_type=PartOfSpeech.NOUN, language=Language.NL)]
    await service.add_words(words)


@pytest.mark.asyncio
async def test_background_translation_failure_surfaces_during_cleanup() -> None:
    """Regression: wait_for_background_translations raises original failure from background task."""
    translator = FailingTranslator()
    service = _create_service(translator)

    await _add_test_words(service)

    # Cleanup should surface the original failure, not execute replay
    with pytest.raises(RuntimeError, match="Translation service unavailable"):
        await service.wait_for_background_translations()

    # Verify translator was called exactly once (no replay)
    assert translator.call_count == 1


@pytest.mark.asyncio
async def test_background_translation_failure_surfaces_after_task_completion() -> None:
    """Regression: cleanup raises original failure even when task finished before cleanup."""
    translator = FailingTranslator()
    service = _create_service(translator)

    await _add_test_words(service)

    # Wait for background task to complete and finish before calling cleanup
    await asyncio.sleep(0.1)

    # Cleanup should still surface the stored original failure
    with pytest.raises(RuntimeError, match="Translation service unavailable"):
        await service.wait_for_background_translations()

    # Verify translator was called exactly once (no replay)
    assert translator.call_count == 1


@pytest.mark.asyncio
async def test_successful_background_translation_no_cleanup_exception() -> None:
    """Regression: successful translations don't raise during cleanup."""
    translator = SuccessfulTranslator()
    service = _create_service(translator)

    await _add_test_words(service)

    # Cleanup should complete without raising
    await service.wait_for_background_translations()

    # Verify translator was called exactly once (no replay)
    assert translator.call_count == 1


class MixedTranslator:
    """First call fails, subsequent calls succeed."""

    def __init__(self) -> None:
        self.call_count = 0

    async def translate(self, words: list[Word]) -> list[Word]:
        self.call_count += 1
        if self.call_count == 1:
            raise RuntimeError("First translation failed")
        return [Word(normalized_form="тест", word_type=PartOfSpeech.NOUN, language=Language.RU) for _ in words]


@pytest.mark.asyncio
async def test_multiple_background_tasks_first_failure_surfaces() -> None:
    """Regression: with multiple tasks, first failure is surfaced without replay."""
    translator = MixedTranslator()
    service = _create_service(translator)

    # Add words multiple times to create multiple background tasks
    words1 = [Word(normalized_form="test1", word_type=PartOfSpeech.NOUN, language=Language.NL)]
    words2 = [Word(normalized_form="test2", word_type=PartOfSpeech.NOUN, language=Language.NL)]

    await service.add_words(words1)  # This will fail
    await service.add_words(words2)  # This will succeed

    # Cleanup should surface the first failure (original, not replayed)
    with pytest.raises(RuntimeError, match="First translation failed"):
        await service.wait_for_background_translations()

    # Verify both translators were called exactly once (no replays)
    assert translator.call_count == 2


@pytest.mark.asyncio
async def test_no_background_tasks_cleanup_completes_normally() -> None:
    """Regression: cleanup works when no background tasks exist."""
    service = _create_service(translator=None)

    # This should complete immediately without error
    await service.wait_for_background_translations()


@pytest.mark.asyncio
async def test_cleanup_clears_stored_exceptions_after_raising() -> None:
    """Regression: stored exceptions are cleared after being surfaced."""
    translator = FailingTranslator()
    service = _create_service(translator)

    await _add_test_words(service)

    # First cleanup should surface the failure
    with pytest.raises(RuntimeError, match="Translation service unavailable"):
        await service.wait_for_background_translations()

    # Second cleanup should complete normally (exceptions cleared)
    await service.wait_for_background_translations()

    # Verify translator was called exactly once total
    assert translator.call_count == 1
