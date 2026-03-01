import re

_WORD_RE = re.compile(r"[A-Za-z]+")


def extract_words_from_text(text: str) -> list[str]:
    return [match.group(0).lower() for match in _WORD_RE.finditer(text)]
