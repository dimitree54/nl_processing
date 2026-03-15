class APIError(Exception):
    """Wraps upstream OpenAI/LangChain API failures."""


class UnsupportedImageFormatError(Exception):
    """Raised when the image format is not supported by the OpenAI API."""


class TargetLanguageNotFoundInInputError(RuntimeError):
    """Raised at runtime when the provided input text is not in the required target language."""


class UnsupportedLanguageError(ValueError):
    """Raised during initialization when a caller requests a language a module does not implement."""
