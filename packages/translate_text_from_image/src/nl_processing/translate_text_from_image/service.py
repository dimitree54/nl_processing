import pathlib

from langchain_core.messages import HumanMessage
from nl_processing.core.exceptions import APIError, TargetLanguageNotFoundError
from nl_processing.core.image_encoding import (
    encode_cv2_to_base64,
    encode_path_to_base64,
    validate_image_format,
)
from nl_processing.core.models import Language
from nl_processing.core.prompts import build_translation_chain
import numpy
from pydantic import BaseModel

_PROMPTS_DIR = pathlib.Path(__file__).parent / "prompts"

_SUPPORTED_PAIRS: set[tuple[str, str]] = {("nl", "ru")}


class _TranslatedImageText(BaseModel):
    text: str


class ImageTextTranslator:
    """Translate text from images in a single LLM call.

    Usage:
        translator = ImageTextTranslator(
            source_language=Language.NL,
            target_language=Language.RU,
        )
        result = await translator.translate_from_path("image.png")
        result = await translator.translate_from_cv2(cv2_image)
    """

    def __init__(
        self,
        *,
        source_language: Language,
        target_language: Language,
        model: str = "gpt-4.1-mini",
        reasoning_effort: str | None = None,
        service_tier: str | None = None,
        temperature: float | None = 0,
    ) -> None:
        self._source_language = source_language
        self._target_language = target_language
        self._chain = build_translation_chain(
            source_language=source_language,
            target_language=target_language,
            supported_pairs=_SUPPORTED_PAIRS,
            prompts_dir=_PROMPTS_DIR,
            tool_schema=_TranslatedImageText,
            model=model,
            reasoning_effort=reasoning_effort,
            service_tier=service_tier,
            temperature=temperature,
        )

    async def translate_from_path(self, path: str) -> str:
        """Translate text from image at the given file path.

        Returns translated text in the target language.
        """
        validate_image_format(path)
        base64_string, media_type = encode_path_to_base64(path)
        return await self._atranslate(base64_string, media_type)

    async def translate_from_cv2(self, image: "numpy.ndarray") -> str:
        """Translate text from OpenCV image array.

        Returns translated text in the target language.
        """
        base64_string, media_type = encode_cv2_to_base64(image)
        return await self._atranslate(base64_string, media_type)

    async def _atranslate(self, base64_string: str, media_type: str) -> str:
        """Internal: run the translation chain with the base64 image."""
        human_message = HumanMessage(
            content=[
                {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{base64_string}"}},
            ]
        )
        try:
            response = await self._chain.ainvoke({"images": [human_message]})
            result = _TranslatedImageText(**response.tool_calls[0]["args"])
        except Exception as e:
            raise APIError(str(e)) from e

        if not result.text.strip():
            msg = "No text in the source language was found in the image"
            raise TargetLanguageNotFoundError(msg)

        return result.text
