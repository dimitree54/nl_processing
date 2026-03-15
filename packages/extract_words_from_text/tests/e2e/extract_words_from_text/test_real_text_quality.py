"""E2e quality tests using OCR ground-truth text from extract_text_from_image."""

from nl_processing.core.models import Language
import pytest

from nl_processing.extract_words_from_text.service import WordExtractor
from tests.e2e.extract_words_from_text.assertions import (
    assert_words_match_contract,
    format_diff,
    word_pairs,
)

# ---------------------------------------------------------------------------
# Text 1 — Dutch textbook vocabulary list (16 entries)
# Source: test_real_photo_dutch_vocabulary_extraction ground truth
# ---------------------------------------------------------------------------
VOCABULARY_LIST_TEXT = (
    "vandaan\n"
    "veranderen\n"
    "verbeteren\n"
    "vlakbij\n"
    "volgorde, de\n"
    "voorbeeld, het\n"
    "voornaam, de\n"
    "vorm, de\n"
    "vraag, de\n"
    "vriendin, de\n"
    "vrouw, de\n"
    "wat\n"
    "week, de\n"
    "welkom\n"
    "werken\n"
    "wonen"
)

VOCABULARY_LIST_EXPECTED: set[tuple[str, str]] = {
    ("vandaan", "adverb"),
    ("veranderen", "verb"),
    ("verbeteren", "verb"),
    ("vlakbij", "adverb"),
    ("de volgorde", "noun"),
    ("het voorbeeld", "noun"),
    ("de voornaam", "noun"),
    ("de vorm", "noun"),
    ("de vraag", "noun"),
    ("de vriendin", "noun"),
    ("de vrouw", "noun"),
    ("wat", "pronoun"),
    ("de week", "noun"),
    ("welkom", "adjective"),
    ("werken", "verb"),
    ("wonen", "verb"),
}

ROTATED_VOCABULARY_TEXT = (
    "klein\n"
    "kloppen\n"
    "komen\n"
    "land, het\n"
    "luisteren\n"
    "maken\n"
    "man, de\n"
    "medecursist, de\n"
    "meneer, de\n"
    "met\n"
    "mevrouw, de\n"
    "mijn\n"
    "naam, de\n"
    "naar\n"
    "nationaliteit, de\n"
    "nazeggen\n"
    "nee\n"
    "neutraal\n"
    "niet\n"
    "nieuw"
)

ROTATED_VOCABULARY_EXPECTED: set[tuple[str, str]] = {
    ("klein", "adjective"),
    ("kloppen", "verb"),
    ("komen", "verb"),
    ("het land", "noun"),
    ("luisteren", "verb"),
    ("maken", "verb"),
    ("de man", "noun"),
    ("de medecursist", "noun"),
    ("de meneer", "noun"),
    ("met", "preposition"),
    ("de mevrouw", "noun"),
    ("mijn", "pronoun"),
    ("de naam", "noun"),
    ("naar", "preposition"),
    ("de nationaliteit", "noun"),
    ("nazeggen", "verb"),
    ("nee", "interjection"),
    ("neutraal", "adjective"),
    ("niet", "adverb"),
    ("nieuw", "adjective"),
}

REAL_OCR_TEXT_CORPUS = f"{VOCABULARY_LIST_TEXT}\n\n{ROTATED_VOCABULARY_TEXT}"
REAL_OCR_EXPECTED = VOCABULARY_LIST_EXPECTED | ROTATED_VOCABULARY_EXPECTED


@pytest.mark.asyncio
async def test_real_ocr_vocabulary_corpus_quality() -> None:
    """E2e quality: one extraction call validates both OCR-derived vocabulary corpora."""
    extractor = WordExtractor()
    result = await extractor.extract(REAL_OCR_TEXT_CORPUS)
    assert_words_match_contract(result, language=Language.NL)

    actual = word_pairs(result)
    expected_fixed = {entry for entry in REAL_OCR_EXPECTED if entry[0] != "vlakbij"}
    actual_fixed = {entry for entry in actual if entry[0] != "vlakbij"}

    assert actual_fixed == expected_fixed, (
        f"Real OCR corpus extraction mismatch:\n{format_diff(expected_fixed, actual_fixed)}"
    )
    assert any(form == "vlakbij" and word_type in {"adverb", "preposition"} for form, word_type in actual)
