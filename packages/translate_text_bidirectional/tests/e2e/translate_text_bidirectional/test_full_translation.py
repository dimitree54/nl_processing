from nl_processing.core.models import Language
import pytest

from nl_processing.translate_text_bidirectional.service import BidirectionalTextTranslator


@pytest.mark.asyncio
async def test_full_translation_nl_to_ru() -> None:
    """E2e: translate multi-paragraph Dutch markdown → Russian."""
    dutch_text = (
        "# Introductie\n\n"
        "Nederland is een klein maar **dichtbevolkt** land in West-Europa.\n\n"
        "## Geografie\n\n"
        "Het land ligt grotendeels *onder zeeniveau* en wordt beschermd door dijken.\n\n"
        "## Cultuur\n\n"
        "De Nederlanders staan bekend om hun:\n\n"
        "- Tolerantie\n"
        "- Directheid\n"
        "- Liefde voor fietsen"
    )
    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    result = await translator.translate(dutch_text)
    assert isinstance(result, str)
    assert len(result.strip()) > 0, "NL→RU translation should produce non-empty output"


@pytest.mark.asyncio
async def test_full_translation_ru_to_nl() -> None:
    """E2e: translate multi-paragraph Russian markdown → Dutch."""
    russian_text = (
        "# Введение\n\n"
        "Россия — это огромная и **многообразная** страна в Восточной Европе и Северной Азии.\n\n"
        "## География\n\n"
        "Страна простирается от *Балтийского моря* до Тихого океана.\n\n"
        "## Культура\n\n"
        "Россия известна своими:\n\n"
        "- Литературой\n"
        "- Музыкой\n"
        "- Балетом"
    )
    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    result = await translator.translate(russian_text)
    assert isinstance(result, str)
    assert len(result.strip()) > 0, "RU→NL translation should produce non-empty output"


@pytest.mark.asyncio
async def test_empty_input_handling() -> None:
    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    result = await translator.translate("")
    assert result == ""


@pytest.mark.asyncio
async def test_markdown_heavy_nl_to_ru() -> None:
    dutch_markdown = (
        "# Hoofdstuk 1\n\n## Sectie 1.1\n\n"
        "Dit is een **vetgedrukt** en *cursief* woord.\n\n"
        "### Subsectie\n\n- Punt een\n- Punt twee\n  - Sub punt\n- Punt drie"
    )
    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    result = await translator.translate(dutch_markdown)
    assert "#" in result
    assert "**" in result
    assert "- " in result


@pytest.mark.asyncio
async def test_markdown_heavy_ru_to_nl() -> None:
    russian_markdown = (
        "# Глава 1\n\n## Раздел 1.1\n\n"
        "Это **жирный** и *курсивный* текст.\n\n"
        "### Подраздел\n\n- Пункт один\n- Пункт два\n  - Подпункт\n- Пункт три"
    )
    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    result = await translator.translate(russian_markdown)
    assert "#" in result
    assert "**" in result
    assert "- " in result


@pytest.mark.asyncio
async def test_short_sentence_nl_to_ru() -> None:
    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    result = await translator.translate("Goede morgen, hoe gaat het?")
    assert len(result.strip()) > 0


@pytest.mark.asyncio
async def test_short_sentence_ru_to_nl() -> None:
    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    result = await translator.translate("Доброе утро, как дела?")
    assert len(result.strip()) > 0


def test_unsupported_pair_raises_at_init() -> None:
    with pytest.raises(ValueError, match="Unsupported language pair"):
        BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.NL)
