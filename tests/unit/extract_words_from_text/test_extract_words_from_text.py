from nl_processing import extract_words_from_text


def test_extract_words_from_text_returns_lowercase_words() -> None:
    words = extract_words_from_text("Hello, NLP world! 2026")
    assert words == ["hello", "nlp", "world"]
