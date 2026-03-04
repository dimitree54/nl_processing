"""E2e quality test: translate words extracted from the De Ruijter product box.

Input words come from the hand-labelled ground truth in the extract_words_from_text
few-shot example #6 (product packaging text).  We translate them NL→RU and verify
each translation against a set of acceptable Russian equivalents.
"""

import pytest

from nl_processing.core.models import Language
from nl_processing.translate_word.service import WordTranslator

# (Dutch normalized_form, set of acceptable Russian translations)
# Multiple acceptable translations account for valid synonyms.
PRODUCT_BOX_WORDS: list[tuple[str, set[str]]] = [
    ("kunnen", {"мочь", "уметь"}),
    ("genieten", {"наслаждаться", "получать удовольствие"}),
    ("elk", {"каждый", "каждая", "каждое", "всякий"}),
    ("de dag", {"день"}),
    ("breed", {"широкий"}),
    ("het assortiment", {"ассортимент"}),
    ("smakelijk", {"вкусный"}),
    ("het product", {"продукт", "товар"}),
    ("de chocoladevlokken", {"шоколадные хлопья", "шоколадная стружка"}),
    ("de melk", {"молоко"}),
    ("puur", {"чистый", "горький", "тёмный", "темный"}),
    ("de chocoladehagel", {"шоколадная посыпка", "шоколадная крошка"}),
    ("de vruchtenhagel", {"фруктовая посыпка", "фруктовая крошка"}),
    ("de anijshagel", {"анисовая посыпка", "анисовая крошка"}),
    ("roze", {"розовый", "розовая", "розовое"}),
    ("wit", {"белый", "белая", "белое"}),
    ("blauw", {"голубой", "синий", "голубая", "синяя"}),
    ("De Ruijter", {"Де Рёйтер", "Де Рюйтер", "Де Рейтер", "De Ruijter"}),
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
        actual = results[i].translation
        acceptable_lower = {_normalize(a) for a in acceptable}
        if _normalize(actual) not in acceptable_lower:
            failures.append(f"  [{dutch!r}] -> got {actual!r}, expected one of {sorted(acceptable)}")

    assert not failures, f"Translation quality failures ({len(failures)}/{len(words)}):\n" + "\n".join(failures)
