import pathlib

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from nl_processing.core.exceptions import APIError, TargetLanguageNotFoundError
from nl_processing.core.image_encoding import (
    encode_cv2_to_base64,
    encode_path_to_base64,
    validate_image_format,
)
from nl_processing.core.models import ExtractedText, Language
from nl_processing.core.prompts import load_prompt
import numpy

# Resolve prompts directory relative to this file
_PROMPTS_DIR = pathlib.Path(__file__).parent / "prompts"


class ImageTextExtractor:
    """Extract language-specific text from images using OpenAI Vision API.

    Usage:
        extractor = ImageTextExtractor()
        text = await extractor.extract_from_path("image.png")
        text = await extractor.extract_from_cv2(cv2_image)
    """

    def __init__(
        self,
        *,
        language: Language = Language.NL,
        model: str = "gpt-5-mini",
        reasoning_effort: str | None = "medium",
        service_tier: str | None = None,
        temperature: float | None = None,
    ) -> None:
        self._language = language
        prompt_path = str(_PROMPTS_DIR / f"{language.value}.json")
        prompt = load_prompt(prompt_path)

        llm = ChatOpenAI(
            model=model, service_tier=service_tier, reasoning_effort=reasoning_effort, temperature=temperature
        ).bind_tools([ExtractedText], tool_choice=ExtractedText.__name__)

        self._chain = prompt | llm

    async def extract_from_path(self, path: str) -> str:
        """Extract text from image at the given file path.

        Returns markdown-formatted text in the target language.
        """
        validate_image_format(path)
        base64_string, media_type = encode_path_to_base64(path)
        return await self._aextract(base64_string, media_type)

    async def extract_from_cv2(self, image: "numpy.ndarray") -> str:
        """Extract text from OpenCV image array.

        Returns markdown-formatted text in the target language.
        """
        base64_string, media_type = encode_cv2_to_base64(image)
        return await self._aextract(base64_string, media_type)

    async def _aextract(self, base64_string: str, media_type: str) -> str:
        """Internal: run the extraction chain with the base64 image."""
        human_message = HumanMessage(
            content=[
                {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{base64_string}"}},
            ]
        )
        try:
            response = await self._chain.ainvoke({"images": [human_message]})
            result = ExtractedText(**response.tool_calls[0]["args"])  # type: ignore[attr-defined]
        except Exception as e:
            raise APIError(str(e)) from e

        # Check if target language text was found
        if not result.text.strip():
            msg = "No text in the target language was found in the image"
            raise TargetLanguageNotFoundError(msg)

        return result.text
