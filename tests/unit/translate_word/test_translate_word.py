from nl_processing import translate_word


def test_translate_word_known_value() -> None:
    assert translate_word("hello", "nl") == "hallo"


def test_translate_word_fallback_for_unknown_word() -> None:
    assert translate_word("tree", "nl") == "tree->nl"
