"""E2e quality test: translate the De Ruijter product box text NL→RU.

Uses key-term spot-checking: for a known Dutch input we define Russian
terms/substrings that any reasonable translation must contain, plus a
Cyrillic-ratio check to confirm the output is actually in Russian.
"""

import re

from nl_processing.core.models import Language
import pytest

from nl_processing.translate_text.service import TextTranslator

PRODUCT_BOX_TEXT = (
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

# Each entry: (description, list of alternative substrings — at least one must appear)
# All checks are case-insensitive substring matches against the full translation.
EXPECTED_KEY_TERMS: list[tuple[str, list[str]]] = [
    ("brand name De Ruijter", ["Де Рёйтер", "Де Рюйтер", "Де Рейтер", "De Ruijter"]),
    ("каждый день (elke dag)", ["каждый день", "ежедневно"]),
    ("наслаждаться/наслажд (genieten)", ["наслажд", "удовольстви"]),
    ("ассортимент (assortiment)", ["ассортимент"]),
    ("вкусн (smakelijke)", ["вкусн"]),
    ("продукт (producten)", ["продукт"]),
    ("шоколад (chocolade-)", ["шоколад"]),
    ("молок (melk)", ["молок", "молоч"]),
    ("фрукт (vruchten-)", ["фрукт"]),
    ("анис (anijs-)", ["анис"]),
    ("бел (witte)", ["бел"]),
    ("голуб/син (blauwe)", ["голуб", "син"]),
    ("розов (rose)", ["розов"]),
]

_CYRILLIC_RE = re.compile(r"[а-яёА-ЯЁ]")
_ALPHA_RE = re.compile(r"[a-zA-Zа-яёА-ЯЁ]")
MIN_CYRILLIC_RATIO = 1.0


@pytest.mark.asyncio
async def test_product_box_translation_quality() -> None:
    """E2e quality: translate product box text and verify key terms + Cyrillic ratio."""
    translator = TextTranslator(source_language=Language.NL, target_language=Language.RU)
    result = await translator.translate(PRODUCT_BOX_TEXT)

    result_without_brand = re.sub(r"De Ruijter", "", result)
    alpha_chars = _ALPHA_RE.findall(result_without_brand)
    cyrillic_chars = _CYRILLIC_RE.findall(result_without_brand)
    ratio = len(cyrillic_chars) / len(alpha_chars) if alpha_chars else 0
    assert ratio >= MIN_CYRILLIC_RATIO, (
        f"Cyrillic ratio {ratio:.0%} below {MIN_CYRILLIC_RATIO:.0%} — output may not be Russian"
    )

    result_lower = result.lower()
    missing: list[str] = []
    for description, alternatives in EXPECTED_KEY_TERMS:
        if not any(alt.lower() in result_lower for alt in alternatives):
            missing.append(f"  - {description}: none of {alternatives} found")

    assert not missing, (
        f"Key term failures ({len(missing)}/{len(EXPECTED_KEY_TERMS)}):\n"
        + "\n".join(missing)
        + f"\n\nFull output:\n{result}"
    )
