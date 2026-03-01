from nl_processing import normalize_text


def test_normalize_text_trims_collapses_and_lowercases() -> None:
    assert normalize_text("  Hello   WORLD  ") == "hello world"
