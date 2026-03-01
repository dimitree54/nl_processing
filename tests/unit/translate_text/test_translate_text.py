from nl_processing import translate_text


def test_translate_text_prefixes_target_language() -> None:
    assert translate_text("hello world", "nl") == "[nl] hello world"
