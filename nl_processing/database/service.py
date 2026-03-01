def save_translation(storage: dict[str, str], source_text: str, translated_text: str) -> None:
    storage[source_text] = translated_text
