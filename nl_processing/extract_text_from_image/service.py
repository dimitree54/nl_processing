import pathlib

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
import numpy

from nl_processing.core.exceptions import APIError, TargetLanguageNotFoundError
from nl_processing.core.models import ExtractedText, Language
from nl_processing.core.prompts import load_prompt
from nl_processing.extract_text_from_image.image_encoding import (
    encode_cv2_to_base64,
    encode_path_to_base64,
    validate_image_format,
)

# Resolve prompts directory relative to this file
_PROMPTS_DIR = pathlib.Path(__file__).parent / "prompts"


class ImageTextExtractor:
    """Extract language-specific text from images using OpenAI Vision API.

    Usage:
        extractor = ImageTextExtractor()
        text = extractor.extract_from_path("image.png")
        text = extractor.extract_from_cv2(cv2_image)
    """

    def __init__(self, *, language: Language = Language.NL, model: str = "gpt-5-mini") -> None:
        self._language = language
        prompt_path = str(_PROMPTS_DIR / f"{language.value}.json")
        self._system_prompt = load_prompt(prompt_path)
        self._llm = ChatOpenAI(
            model=model,
        ).with_structured_output(ExtractedText)

    def extract_from_path(self, path: str) -> str:
        """Extract text from image at the given file path.

        Returns markdown-formatted text in the target language.
        """
        validate_image_format(path)
        base64_string, media_type = encode_path_to_base64(path)
        return self._extract(base64_string, media_type)

    def extract_from_cv2(self, image: "numpy.ndarray") -> str:
        """Extract text from OpenCV image array.

        Returns markdown-formatted text in the target language.
        """
        base64_string, media_type = encode_cv2_to_base64(image)
        return self._extract(base64_string, media_type)

    def _extract(self, base64_string: str, media_type: str) -> str:
        """Internal: run the extraction chain with the base64 image."""
        system_messages = self._system_prompt.format_messages()
        human_message = HumanMessage(
            content=[
                {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{base64_string}"}},
            ]
        )
        messages = [*system_messages, human_message]
        try:
            result = self._llm.invoke(messages)
        except Exception as e:
            raise APIError(str(e)) from e

        # Extract text from result
        if isinstance(result, ExtractedText):
            text = result.text
        else:
            # Handle dict response from structured output
            text = result["text"]

        # Check if target language text was found
        if not text.strip():
            msg = "No text in the target language was found in the image"
            raise TargetLanguageNotFoundError(msg)

        return text
