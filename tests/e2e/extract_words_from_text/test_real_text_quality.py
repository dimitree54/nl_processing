"""E2e quality tests: extract words from real texts produced by extract_text_from_image.

These texts are the ground-truth outputs of the image extraction e2e tests
(tests/e2e/extract_text_from_image/test_full_extraction.py).  We feed them
into extract_words_from_text and verify the result against hand-labelled
expected words using set-based comparison on (normalized_form, word_type).
"""

import pytest

from nl_processing.extract_words_from_text.service import WordExtractor

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

# ---------------------------------------------------------------------------
# Text 2 — Rotated Dutch textbook vocabulary (20 entries)
# Source: test_real_photo_rotated_dutch_english_extraction ground truth
# ---------------------------------------------------------------------------
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


def _to_set(words: list) -> set[tuple[str, str]]:
    return {(w.normalized_form, w.word_type.value) for w in words}


def _format_diff(expected: set, actual: set) -> str:
    missing = expected - actual
    extra = actual - expected
    lines = []
    if missing:
        lines.append(f"  MISSING ({len(missing)}):")
        for form, wtype in sorted(missing):
            lines.append(f"    - ({form!r}, {wtype!r})")
    if extra:
        lines.append(f"  EXTRA ({len(extra)}):")
        for form, wtype in sorted(extra):
            lines.append(f"    + ({form!r}, {wtype!r})")
    return "\n".join(lines)


@pytest.mark.asyncio
async def test_vocabulary_list_quality() -> None:
    """E2e quality: textbook vocabulary list (16 words) — exact set match."""
    extractor = WordExtractor()
    result = await extractor.extract(VOCABULARY_LIST_TEXT)
    actual = _to_set(result)

    assert actual == VOCABULARY_LIST_EXPECTED, (
        f"Vocabulary list extraction mismatch:\n{_format_diff(VOCABULARY_LIST_EXPECTED, actual)}"
    )


@pytest.mark.asyncio
async def test_rotated_vocabulary_quality() -> None:
    """E2e quality: rotated textbook vocabulary (20 words) — exact set match."""
    extractor = WordExtractor()
    result = await extractor.extract(ROTATED_VOCABULARY_TEXT)
    actual = _to_set(result)

    assert actual == ROTATED_VOCABULARY_EXPECTED, (
        f"Rotated vocabulary extraction mismatch:\n{_format_diff(ROTATED_VOCABULARY_EXPECTED, actual)}"
    )
