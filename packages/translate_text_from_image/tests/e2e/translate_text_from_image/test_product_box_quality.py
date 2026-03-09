"""Quality verification for De Ruijter product box image translation.

Validates translation accuracy using key-term matching and Cyrillic ratio analysis
for real-world Dutch product packaging text.
"""

import pathlib
import re

from nl_processing.core.models import Language
import pytest

from nl_processing.translate_text_from_image.service import ImageTextTranslator

_FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"

# Required terms mapping: description → list of acceptable Russian alternatives
REQUIRED_TERMS: dict[str, list[str]] = {
    "brand name preserved": ["Де Рёйтер", "Де Рюйтер", "Де Рейтер", "De Ruijter"],
    "daily enjoyment (elke dag)": ["каждый день", "ежедневно"],
    "enjoyment (genieten)": ["наслажд", "удовольстви"],
    "assortment (assortiment)": ["ассортимент"],
    "tasty (smakelijke)": ["вкусн"],
    "products (producten)": ["продукт"],
    "chocolate (chocolade)": ["шоколад"],
    "milk (melk)": ["молок", "молоч"],
    "fruit (vruchten)": ["фрукт"],
    "anise (anijs)": ["анис"],
    "white (witte)": ["бел"],
    "blue (blauwe)": ["голуб", "син"],
    "pink (rose)": ["розов"],
}

# Regex patterns for character analysis
_CYRILLIC_PATTERN = re.compile(r"[а-яёА-ЯЁ]")
_LETTER_PATTERN = re.compile(r"[a-zA-Zа-яёА-ЯЁ]")
MIN_CYRILLIC_RATIO = 1.0


@pytest.mark.asyncio
async def test_product_box_image_translation_quality() -> None:
    """Verify high-quality translation of De Ruijter product box from image."""
    product_image_path = str(_FIXTURES_DIR / "dutch_product_box.jpg")

    image_translator = ImageTextTranslator(source_language=Language.NL, target_language=Language.RU)
    translation_result = await image_translator.translate_from_path(product_image_path)

    # Remove brand name for Cyrillic ratio calculation
    result_without_brand = re.sub(r"De Ruijter", "", translation_result)
    all_letters = _LETTER_PATTERN.findall(result_without_brand)
    cyrillic_letters = _CYRILLIC_PATTERN.findall(result_without_brand)

    # Calculate and verify Cyrillic ratio
    ratio = len(cyrillic_letters) / len(all_letters) if all_letters else 0
    assert ratio >= MIN_CYRILLIC_RATIO, (
        f"Cyrillic ratio {ratio:.0%} below {MIN_CYRILLIC_RATIO:.0%} threshold — translation may not be properly Russian"
    )

    # Key-term verification with different structure than existing test
    result_normalized = translation_result.lower()
    missing_terms = []

    for term_description, acceptable_alternatives in REQUIRED_TERMS.items():
        term_found = False
        for alternative in acceptable_alternatives:
            if alternative.lower() in result_normalized:
                term_found = True
                break

        if not term_found:
            missing_terms.append(f"  • {term_description}: expected one of {acceptable_alternatives}")

    assert not missing_terms, (
        f"Translation quality check failed - {len(missing_terms)}/{len(REQUIRED_TERMS)} "
        f"required terms missing:\n"
        + "\n".join(missing_terms)
        + f"\n\nComplete translation output:\n{translation_result}"
    )
