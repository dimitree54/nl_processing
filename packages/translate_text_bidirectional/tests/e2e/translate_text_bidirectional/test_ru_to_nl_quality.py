import re
import time

from nl_processing.core.models import Language
import pytest

from nl_processing.translate_text_bidirectional.service import BidirectionalTextTranslator

LLM_CHATTER_PREFIXES = [
    "Here is",
    "Translation:",
    "Sure,",
    "Of course",
    "The translation",
    "Below is",
    "Certainly",
]


@pytest.mark.asyncio
async def test_ru_to_nl_output_cleanliness() -> None:
    """BT-FR4: RU→NL output must not contain LLM chatter prefixes."""
    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    result = await translator.translate("Кот сидит на коврике и смотрит на птиц за окном.")

    assert isinstance(result, str)
    assert len(result.strip()) > 0, "Translation should not be empty"

    for prefix in LLM_CHATTER_PREFIXES:
        assert not result.startswith(prefix), f"Output starts with LLM chatter prefix: '{prefix}'"


@pytest.mark.asyncio
async def test_ru_to_nl_latin_only_output() -> None:
    """Success Criteria: RU→NL output contains only Latin characters (no Cyrillic) for text without proper nouns."""
    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    result = await translator.translate("Кот сидит на коврике и смотрит на птиц за окном.")

    assert isinstance(result, str)
    assert len(result.strip()) > 0, "Translation should not be empty"
    assert not re.search(r"[\u0400-\u04FF]", result), f"Cyrillic characters found in: {result}"


@pytest.mark.asyncio
async def test_ru_to_nl_markdown_structure_preservation() -> None:
    """BT-FR2: RU→NL markdown formatting must be preserved in translation."""
    russian_markdown = (
        "# Важная информация\n\n"
        "Это **важное** сообщение с *курсивным* текстом.\n\n"
        "- Первый пункт\n"
        "- Второй пункт\n"
        "- Третий пункт"
    )

    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    result = await translator.translate(russian_markdown)

    assert isinstance(result, str)
    assert result.startswith("#"), f"Heading not preserved. Output: {result}"
    assert "**" in result, f"Bold markdown not preserved. Output: {result}"
    assert "- " in result, f"List items not preserved. Output: {result}"


@pytest.mark.asyncio
async def test_performance_ru_to_nl() -> None:
    """BT-NFR1: RU→NL translation of ~100 words must complete in <5 seconds."""
    russian_text = (
        "Россия - огромная страна, расположенная в Восточной Европе и Северной Азии. "
        "Она известна своими бескрайними просторами, богатой культурой и историей. "
        "Москва является столицей и крупнейшим городом страны. "
        "Русская литература включает произведения великих писателей как Толстой и Достоевский. "
        "Климат варьируется от арктического на севере до субтропического на юге. "
        "Традиционная русская кухня включает борщ, блины и другие блюда. "
        "Балет и классическая музыка являются важными частями культурного наследия. "
        "Образование высоко ценится и доступно для всех граждан. "
        "Природа страны разнообразна - от тайги до степей и гор. "
        "Экономика основана на природных ресурсах и промышленности."
    )

    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)

    start = time.time()
    result = await translator.translate(russian_text)
    elapsed = time.time() - start

    assert isinstance(result, str)
    assert len(result.strip()) > 0, "Translation should not be empty"
    assert elapsed < 5, f"Translation took {elapsed:.2f}s — exceeds 5.00s QA gate"
