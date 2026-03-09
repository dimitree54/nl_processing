"""E2e quality test: translate words extracted from the De Ruijter product box.

Input words come from the hand-labelled ground truth in the extract_words_from_text
few-shot example #6 (product packaging text).  We translate them NL->RU and verify
each translation against a set of acceptable Russian equivalents.
"""

from nl_processing.core.models import Language, PartOfSpeech, Word
import pytest

from nl_processing.translate_word.service import WordTranslator

# (Dutch Word, set of acceptable Russian translations)
# Multiple acceptable translations account for valid synonyms.
PRODUCT_BOX_WORDS: list[tuple[Word, set[str]]] = [
    (Word(normalized_form="kunnen", word_type=PartOfSpeech.VERB, language=Language.NL), {"мочь", "уметь"}),
    (
        Word(normalized_form="genieten", word_type=PartOfSpeech.VERB, language=Language.NL),
        {"наслаждаться", "получать удовольствие"},
    ),
    (
        Word(normalized_form="elk", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL),
        {"каждый", "каждая", "каждое", "всякий"},
    ),
    (Word(normalized_form="de dag", word_type=PartOfSpeech.NOUN, language=Language.NL), {"день"}),
    (Word(normalized_form="breed", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL), {"широкий"}),
    (Word(normalized_form="het assortiment", word_type=PartOfSpeech.NOUN, language=Language.NL), {"ассортимент"}),
    (Word(normalized_form="smakelijk", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL), {"вкусный"}),
    (Word(normalized_form="het product", word_type=PartOfSpeech.NOUN, language=Language.NL), {"продукт", "товар"}),
    (
        Word(normalized_form="de chocoladevlokken", word_type=PartOfSpeech.NOUN, language=Language.NL),
        {"шоколадные хлопья", "шоколадная стружка"},
    ),
    (Word(normalized_form="de melk", word_type=PartOfSpeech.NOUN, language=Language.NL), {"молоко"}),
    (
        Word(normalized_form="puur", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL),
        {"чистый", "горький", "тёмный", "темный", "натуральный"},
    ),
    (
        Word(normalized_form="de chocoladehagel", word_type=PartOfSpeech.NOUN, language=Language.NL),
        {"шоколадная посыпка", "шоколадная крошка"},
    ),
    (
        Word(normalized_form="de vruchtenhagel", word_type=PartOfSpeech.NOUN, language=Language.NL),
        {"фруктовая посыпка", "фруктовая крошка"},
    ),
    (
        Word(normalized_form="de anijshagel", word_type=PartOfSpeech.NOUN, language=Language.NL),
        {"анисовая посыпка", "анисовая крошка"},
    ),
    (
        Word(normalized_form="roze", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL),
        {"розовый", "розовая", "розовое"},
    ),
    (Word(normalized_form="wit", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL), {"белый", "белая", "белое"}),
    (
        Word(normalized_form="blauw", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL),
        {"голубой", "синий", "голубая", "синяя"},
    ),
    (
        Word(normalized_form="De Ruijter", word_type=PartOfSpeech.PROPER_NOUN_PERSON, language=Language.NL),
        {"Де Рёйтер", "Де Рюйтер", "Де Рейтер", "De Ruijter"},
    ),
]


def _normalize(text: str) -> str:
    return text.strip().lower()


@pytest.mark.asyncio
async def test_product_box_translation_quality() -> None:
    """E2e quality: translate 18 words from the product box and verify each translation."""
    translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)

    words = [w for w, _ in PRODUCT_BOX_WORDS]
    results = await translator.translate(words)

    assert len(results) == len(words), f"Expected {len(words)} results, got {len(results)}"

    failures: list[str] = []
    for i, (dutch, acceptable) in enumerate(PRODUCT_BOX_WORDS):
        actual = results[i].normalized_form
        acceptable_lower = {_normalize(a) for a in acceptable}
        if _normalize(actual) not in acceptable_lower:
            failures.append(f"  [{dutch.normalized_form!r}] -> got {actual!r}, expected one of {sorted(acceptable)}")

    assert not failures, f"Translation quality failures ({len(failures)}/{len(words)}):\n" + "\n".join(failures)
