"""E2e quality tests: bidirectional product box translation with key-term assertions."""

import re

from nl_processing.core.models import Language
import pytest

from nl_processing.translate_text_bidirectional.service import BidirectionalTextTranslator

PRODUCT_BOX_NL = (
    "Met De Ruijter kunt u elke dag genieten "
    "van een breed assortiment smakelijke producten.\n"
    "Chocoladevlokken Melk en Puur\n"
    "Chocoladehagel Melk en Puur\n"
    "Vruchtenhagel\n"
    "Anijshagel\n"
    "Vlokfeest\n"
    "Gestampte Muisjes\n"
    "Rose en Witte Muisjes\n"
    "Blauwe en Witte Muisjes"
)

EXPECTED_KEY_TERMS_NL_TO_RU: list[tuple[str, list[str]]] = [
    ("brand name De Ruijter", ["Де Рёйтер", "Де Рюйтер", "Де Рейтер", "De Ruijter"]),
    ("каждый день (elke dag)", ["каждый день", "ежедневно", "повседневный"]),
    ("наслаждаться (genieten)", ["наслажд", "удовольстви", "радовать"]),
    ("ассортимент (assortiment)", ["ассортимент", "выбор"]),
    ("вкусн (smakelijke)", ["вкусн"]),
    ("продукт (producten)", ["продукт"]),
    ("шоколад (chocolade-)", ["шоколад"]),
    ("молок (melk)", ["молок", "молоч"]),
    ("фрукт (vruchten-)", ["фрукт"]),
    ("анис (anijs-)", ["анис"]),
    ("бел (witte)", ["бел", "белый"]),
    ("голуб/син (blauwe)", ["голуб", "син", "синий"]),
    ("розов (rose)", ["розов", "розовый"]),
]

PRODUCT_BOX_RU = (
    "С высококачественной продукцией Де Рейтер вы можете ежедневно наслаждаться "
    "разнообразным ассортиментом превосходных продуктов.\n"
    "Шоколадные хлопья молочные и тёмные\n"
    "Шоколадная посыпка молочная и тёмная\n"
    "Фруктовая посыпка\n"
    "Анисовая посыпка\n"
    "Праздничные хлопья\n"
    "Толчёные мышки\n"
    "Розовые и белые мышки\n"
    "Голубые и белые мышки"
)

EXPECTED_KEY_TERMS_RU_TO_NL: list[tuple[str, list[str]]] = [
    ("chocolade (шоколад)", ["chocola"]),
    ("melk (молочн)", ["melk", "milk"]),
    ("producten (продукт)", ["product"]),
    ("assortiment (ассортимент)", ["assortiment", "aanbod"]),
    ("genieten (наслаждаться)", ["geniet", "plezier"]),
    ("fruit (фрукт)", ["fruit", "vrucht"]),
    ("anijs (анис)", ["anijs"]),
    ("wit (бел)", ["wit"]),
    ("blauw (голуб)", ["blauw"]),
    ("roze (розов)", ["roz", "ros"]),
]

_CYRILLIC_RE = re.compile(r"[а-яёА-ЯЁ]")
_LATIN_RE = re.compile(r"[a-zA-Z]")
_ALPHA_RE = re.compile(r"[a-zA-Zа-яёА-ЯЁ]")


def _check_key_terms(result: str, expected_terms: list[tuple[str, list[str]]]) -> None:
    """Assert all expected key terms are found in the result."""
    result_lower = result.lower()
    missing: list[str] = []
    for description, alternatives in expected_terms:
        if not any(alt.lower() in result_lower for alt in alternatives):
            missing.append(f"  - {description}: none of {alternatives} found")
    assert not missing, (
        f"Key term failures ({len(missing)}/{len(expected_terms)}):\n"
        + "\n".join(missing)
        + f"\n\nFull output:\n{result}"
    )


@pytest.mark.asyncio
async def test_product_box_nl_to_ru_quality() -> None:
    """E2e quality: NL→RU product box translation + Cyrillic ratio + key terms."""
    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    result = await translator.translate(PRODUCT_BOX_NL)

    result_without_brand = re.sub(r"De Ruijter", "", result)
    alpha_chars = _ALPHA_RE.findall(result_without_brand)
    cyrillic_chars = _CYRILLIC_RE.findall(result_without_brand)
    ratio = len(cyrillic_chars) / len(alpha_chars) if alpha_chars else 0
    assert ratio >= 1.0, f"Cyrillic ratio {ratio:.0%} below 100% — output may not be Russian"

    _check_key_terms(result, EXPECTED_KEY_TERMS_NL_TO_RU)


@pytest.mark.asyncio
async def test_product_box_ru_to_nl_quality() -> None:
    """E2e quality: RU→NL product box translation + Latin ratio + key terms."""
    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    result = await translator.translate(PRODUCT_BOX_RU)

    alpha_chars = _ALPHA_RE.findall(result)
    latin_chars = _LATIN_RE.findall(result)
    ratio = len(latin_chars) / len(alpha_chars) if alpha_chars else 0
    assert ratio >= 1.0, f"Latin ratio {ratio:.0%} below 100% — output may not be Dutch"

    _check_key_terms(result, EXPECTED_KEY_TERMS_RU_TO_NL)
