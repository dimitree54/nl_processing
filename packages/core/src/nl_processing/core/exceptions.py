class APIError(Exception):
    """Wraps upstream OpenAI/LangChain API failures."""


class TargetLanguageNotFoundError(Exception):
    """Raised when no text in the target language is detected."""


class UnsupportedImageFormatError(Exception):
    """Raised when the image format is not supported by the OpenAI API."""
