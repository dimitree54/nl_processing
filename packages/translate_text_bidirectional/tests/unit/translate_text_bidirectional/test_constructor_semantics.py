"""Unit tests for constructor semantics and source-anchored behavior."""

from nl_processing.core.models import Language
import pytest

from nl_processing.translate_text_bidirectional.service import BidirectionalTextTranslator
from tests.unit.translate_text_bidirectional.conftest import (
    _AsyncChainMock,
    make_nl_to_ru_response,
    make_ru_to_nl_response,
)


@pytest.mark.asyncio
async def test_source_anchored_semantics_nl_source(monkeypatch: pytest.MonkeyPatch) -> None:
    """For source=NL,target=RU: NL->RU, non-NL->NL."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)

    # Dutch (source) input -> Russian (target) output via NL->RU tool
    translator._chain = _AsyncChainMock(make_nl_to_ru_response("Результат"))
    result = await translator.translate("Nederlandse tekst")
    assert result == "Результат"

    # Russian (non-source) input -> Dutch (source) output via RU->NL tool
    translator._chain = _AsyncChainMock(make_ru_to_nl_response("Nederlandse tekst"))
    result = await translator.translate("Русский текст")
    assert result == "Nederlandse tekst"

    # English (non-source) input -> Dutch (source) output via RU->NL tool
    translator._chain = _AsyncChainMock(make_ru_to_nl_response("Nederlandse tekst"))
    result = await translator.translate("English text")
    assert result == "Nederlandse tekst"


@pytest.mark.asyncio
async def test_source_anchored_semantics_ru_source(monkeypatch: pytest.MonkeyPatch) -> None:
    """For source=RU,target=NL: RU->NL, non-RU->RU."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    translator = BidirectionalTextTranslator(source_language=Language.RU, target_language=Language.NL)

    # Russian (source) input -> Dutch (target) output via RU->NL tool
    translator._chain = _AsyncChainMock(make_ru_to_nl_response("Nederlandse tekst"))
    result = await translator.translate("Русский текст")
    assert result == "Nederlandse tekst"

    # Dutch (non-source) input -> Russian (source) output via NL->RU tool
    translator._chain = _AsyncChainMock(make_nl_to_ru_response("Результат"))
    result = await translator.translate("Nederlandse tekst")
    assert result == "Результат"

    # English (non-source) input -> Russian (source) output via NL->RU tool
    translator._chain = _AsyncChainMock(make_nl_to_ru_response("Результат"))
    result = await translator.translate("English text")
    assert result == "Результат"


@pytest.mark.asyncio
async def test_constructor_order_semantic_difference(monkeypatch: pytest.MonkeyPatch) -> None:
    """Constructor parameter order creates observably different behavior for same input."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    # Both configurations accept same languages but define opposite semantics
    nl_source_translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    ru_source_translator = BidirectionalTextTranslator(source_language=Language.RU, target_language=Language.NL)

    # For English input, directions should be opposite between the two configurations
    # source=NL: English -> Dutch (using RU->NL tool)
    nl_source_translator._chain = _AsyncChainMock(make_ru_to_nl_response("Nederlandse uitvoer"))
    result_nl_source = await nl_source_translator.translate("English input")

    # source=RU: English -> Russian (using NL->RU tool)
    ru_source_translator._chain = _AsyncChainMock(make_nl_to_ru_response("Русский вывод"))
    result_ru_source = await ru_source_translator.translate("English input")

    assert result_nl_source == "Nederlandse uitvoer"
    assert result_ru_source == "Русский вывод"
    assert result_nl_source != result_ru_source, "Constructor order should create different behavior"


def test_public_api_exposure() -> None:
    """BidirectionalTextTranslator can be imported from package root."""
    # Import inside function to avoid top-level import issues
    import nl_processing.translate_text_bidirectional as public_module  # noqa: PLC0415
    import nl_processing.translate_text_bidirectional.service as service_module  # noqa: PLC0415

    # Should be the same class
    assert public_module.BidirectionalTextTranslator is service_module.BidirectionalTextTranslator
    assert public_module.BidirectionalTextTranslator.__name__ == "BidirectionalTextTranslator"
