import pathlib
from typing import NotRequired, TypedDict

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from nl_processing.core.exceptions import (
    APIError,
    TargetLanguageNotFoundError,
    UnsupportedLanguageError,
)
from nl_processing.core.image_encoding import (
    encode_cv2_to_base64,
    encode_path_to_base64,
    validate_image_format,
)
from nl_processing.core.models import ExtractedText, Language
from nl_processing.core.prompts import load_prompt
import numpy
from pydantic import ValidationError

from nl_processing.extract_text_from_image.exceptions import ImageTextFileNotFoundError

# Resolve prompts directory relative to this file
_PROMPTS_DIR = pathlib.Path(__file__).parent / "prompts"


class _ChatOpenAIKwargs(TypedDict):
    model: str
    service_tier: NotRequired[str]
    reasoning_effort: NotRequired[str]
    temperature: NotRequired[float]


def _build_llm_kwargs(
    *,
    model: str,
    service_tier: str | None,
    reasoning_effort: str | None,
    temperature: float | None,
) -> _ChatOpenAIKwargs:
    kwargs: _ChatOpenAIKwargs = {"model": model}
    if service_tier is not None:
        kwargs["service_tier"] = service_tier
    if reasoning_effort is not None:
        kwargs["reasoning_effort"] = reasoning_effort
    if temperature is not None:
        kwargs["temperature"] = temperature
    return kwargs


def _load_prompt_for_language(language: Language) -> ChatPromptTemplate:
    prompt_path = _PROMPTS_DIR / f"{language.value}.json"
    if not prompt_path.is_file():
        supported_languages = sorted(path.stem for path in _PROMPTS_DIR.glob("*.json"))
        msg = f"Language '{language.value}' is not supported. Supported languages: {', '.join(supported_languages)}"
        raise UnsupportedLanguageError(msg)

    return load_prompt(str(prompt_path))


def _encode_image_path(path: str) -> tuple[str, str]:
    try:
        return encode_path_to_base64(path)
    except FileNotFoundError as exc:
        msg = f"Image file not found: {path}"
        raise ImageTextFileNotFoundError(msg) from exc


def _parse_extracted_text(response: object) -> ExtractedText:
    try:
        return ExtractedText(**response.tool_calls[0]["args"])  # type: ignore[attr-defined]
    except (AttributeError, IndexError, KeyError, TypeError, ValidationError) as exc:
        raise APIError(str(exc)) from exc


class ImageTextExtractor:
    """Asynchronously extract markdown text from images in a target language.

    Construction loads the prompt asset for the requested `language` and binds the
    OpenAI chat model with the provided optional model-shaping parameters.
    Unsupported languages raise `UnsupportedLanguageError` during construction.
    """

    def __init__(
        self,
        *,
        language: Language = Language.NL,
        model: str = "gpt-4.1-mini",
        reasoning_effort: str | None = None,
        service_tier: str | None = None,
        temperature: float | None = 0,
    ) -> None:
        """Create an extractor for one target language.

        Args:
            language: Target language for extracted markdown text.
            model: OpenAI model name used for multimodal extraction.
            reasoning_effort: Optional reasoning setting passed to the model.
            service_tier: Optional service tier passed to the model.
            temperature: Optional sampling temperature passed to the model.

        Raises:
            UnsupportedLanguageError: `language` is not supported by bundled prompt assets.
        """
        self._language = language
        prompt = _load_prompt_for_language(language)

        llm_kwargs = _build_llm_kwargs(
            model=model,
            service_tier=service_tier,
            reasoning_effort=reasoning_effort,
            temperature=temperature,
        )
        llm = ChatOpenAI(**llm_kwargs).bind_tools([ExtractedText], tool_choice=ExtractedText.__name__)

        self._chain = prompt | llm

    async def extract_from_path(self, path: str) -> str:
        """Extract markdown text from a supported image file path.

        Args:
            path: Path to a supported image file.

        Returns:
            Markdown-formatted text in the configured target language.

        Raises:
            UnsupportedImageFormatError: `path` has an unsupported image extension.
            ImageTextFileNotFoundError: `path` does not exist.
            APIError: Upstream invocation or response parsing fails.
            TargetLanguageNotFoundError: Extraction returns blank or whitespace-only text.
        """
        validate_image_format(path)
        base64_string, media_type = _encode_image_path(path)
        return await self._aextract(base64_string, media_type)

    async def extract_from_cv2(self, image: "numpy.ndarray") -> str:
        """Extract markdown text from an in-memory OpenCV image array.

        Args:
            image: OpenCV image array to extract text from.

        Returns:
            Markdown-formatted text in the configured target language.

        Raises:
            APIError: Upstream invocation or response parsing fails.
            TargetLanguageNotFoundError: Extraction returns blank or whitespace-only text.
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
        except Exception as exc:
            raise APIError(str(exc)) from exc

        result = _parse_extracted_text(response)

        # Check if target language text was found
        if not result.text.strip():
            msg = "No text in the target language was found in the image"
            raise TargetLanguageNotFoundError(msg)

        return result.text
