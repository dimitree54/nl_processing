import re


def normalize_text(text: str) -> str:
    """Normalize extracted text for stable comparisons."""
    normalized = re.sub(r"[#*_~`>\-]+", "", text)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip().lower()


def evaluate_extraction(extracted: str, ground_truth: str) -> bool:
    """Compare extracted text against expected text."""
    return normalize_text(extracted) == normalize_text(ground_truth)
