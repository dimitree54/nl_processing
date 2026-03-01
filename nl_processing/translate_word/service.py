_TRANSLATIONS: dict[tuple[str, str], str] = {
    ("hello", "nl"): "hallo",
    ("world", "nl"): "wereld",
}


def translate_word(word: str, target_language: str) -> str:
    key = (word.strip().lower(), target_language)
    if key in _TRANSLATIONS:
        return _TRANSLATIONS[key]
    return f"{word}->{target_language}"
