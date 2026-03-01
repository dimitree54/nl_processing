from pydantic import BaseModel


class MockPayload(BaseModel):
    text: str


def normalize_text(text: str) -> str:
    return " ".join(text.strip().split()).lower()
