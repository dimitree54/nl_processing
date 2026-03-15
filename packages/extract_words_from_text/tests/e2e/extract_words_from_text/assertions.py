from nl_processing.core.models import Language, PartOfSpeech, Word


def assert_words_match_contract(words: list[Word], *, language: Language) -> None:
    assert words, "Expected non-empty result"
    for word in words:
        assert isinstance(word, Word), f"Expected Word, got {type(word)}"
        assert word.normalized_form, "normalized_form must not be empty"
        assert isinstance(word.word_type, PartOfSpeech), "word_type must be PartOfSpeech"
        assert word.language == language, f"Expected {language.value}, got {word.language.value}"


def format_diff(expected: set[tuple[str, str]], actual: set[tuple[str, str]]) -> str:
    missing = expected - actual
    extra = actual - expected
    lines: list[str] = []
    if missing:
        lines.append(f"  MISSING ({len(missing)}):")
        for form, word_type in sorted(missing):
            lines.append(f"    - ({form!r}, {word_type!r})")
    if extra:
        lines.append(f"  EXTRA ({len(extra)}):")
        for form, word_type in sorted(extra):
            lines.append(f"    + ({form!r}, {word_type!r})")
    return "\n".join(lines)


def word_pairs(words: list[Word]) -> set[tuple[str, str]]:
    return {(word.normalized_form, word.word_type.value) for word in words}
