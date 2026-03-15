"""E2E translation tests using real photographs."""

import pathlib
import re

from nl_processing.core.models import Language
import pytest

from nl_processing.translate_text_from_image.service import ImageTextTranslator

_FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"

# Key vocabulary terms that should appear in Russian translation
VOCABULARY_RUSSIAN_TERMS = {
    "откуда": "vandaan",
    "менять": "veranderen",
    "улучш": "verbeteren",
    "рядом": "vlakbij",
    "порядок": "volgorde",
    "пример": "voorbeeld",
    "форм": "vorm",
    "вопрос": "vraag",
    "женщин": "vrouw",
    "недел": "week",
    "работ": "werken",
}

# English terms that should NOT appear in Dutch-only translation
ENGLISH_EXCLUSIONS = ["small", "to knock", "to come", "country", "to listen"]


@pytest.mark.asyncio
async def test_real_photo_dutch_vocabulary_translation() -> None:
    """Translate Dutch vocabulary from real textbook photo, verify Russian output quality."""
    photo_path = str(_FIXTURES_DIR / "dutch_vocabulary.jpg")

    translator = ImageTextTranslator(source_language=Language.NL, target_language=Language.RU)
    translated_content = await translator.translate_from_path(photo_path)

    # Basic validation
    assert translated_content.strip(), "Translation output should not be empty"

    # Verify Cyrillic characters present
    cyrillic_pattern = re.compile(r"[а-яёА-ЯЁ]")
    cyrillic_matches = cyrillic_pattern.findall(translated_content)
    assert cyrillic_matches, "Translation must contain Cyrillic characters"

    # Key-term spot-check: verify at least 6 Russian terms found
    translated_lower = translated_content.lower()
    terms_found = 0

    for russian_term, _ in VOCABULARY_RUSSIAN_TERMS.items():
        if russian_term.lower() in translated_lower:
            terms_found += 1

    minimum_required = 6
    success_rate = terms_found / len(VOCABULARY_RUSSIAN_TERMS)

    assert terms_found >= minimum_required, (
        f"Found only {terms_found}/{len(VOCABULARY_RUSSIAN_TERMS)} Russian terms "
        f"(success rate: {success_rate:.0%}). Expected at least {minimum_required}.\n"
        f"Full translation:\n{translated_content}"
    )

    # Verify at least 50% success rate as specified
    assert success_rate >= 0.5, f"Success rate {success_rate:.0%} below required 50% threshold"


@pytest.mark.asyncio
async def test_real_photo_rotated_bilingual_translates_only_dutch() -> None:
    """Translate rotated bilingual photo, verify Dutch content translated excluding English."""
    rotated_photo_path = str(_FIXTURES_DIR / "dutch_vocabulary_rotated.jpg")

    translator = ImageTextTranslator(source_language=Language.NL, target_language=Language.RU)
    translation_output = await translator.translate_from_path(rotated_photo_path)

    # Verify non-empty Cyrillic output
    assert translation_output.strip(), "Translation should not be empty"

    cyrillic_check = re.compile(r"[а-яёА-ЯЁ]")
    cyrillic_found = cyrillic_check.findall(translation_output)
    assert cyrillic_found, "Translation must contain Cyrillic characters"

    # Verify English words NOT present in output
    output_lowercase = translation_output.lower()
    english_terms_found = []

    for english_term in ENGLISH_EXCLUSIONS:
        if english_term.lower() in output_lowercase:
            english_terms_found.append(english_term)

    assert not english_terms_found, (
        f"English terms should not appear in Dutch-only translation: {english_terms_found}\n"
        f"Full output:\n{translation_output}"
    )
