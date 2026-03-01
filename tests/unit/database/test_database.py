from nl_processing import save_translation


def test_save_translation_stores_value() -> None:
    storage: dict[str, str] = {}
    save_translation(storage, "hello", "hallo")
    assert storage["hello"] == "hallo"
