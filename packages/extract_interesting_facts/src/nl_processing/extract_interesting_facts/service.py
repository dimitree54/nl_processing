import pathlib

from langchain_core.messages import HumanMessage
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from nl_processing.core.exceptions import APIError
from nl_processing.core.models import Language
from nl_processing.core.prompts import build_llm_kwargs, load_prompt

_PROMPTS_DIR = pathlib.Path(__file__).parent / "prompts"
_PROMPT_FILE = "nl_ru_facts.json"
_SUPPORTED_PAIRS: set[tuple[str, str]] = {("nl", "ru")}


def _validate_response(result_text: str, text: str) -> None:
    """Validate response contains minimal expected content.

    Args:
        result_text: The response content from the LLM
        text: The original input text (for context in error messages)

    Raises:
        APIError: If response is empty or too short to be useful
    """
    if not result_text.strip():
        raise APIError("Model returned empty response")

    if len(result_text.strip()) < 10:
        raise APIError(f"Model returned unusably short response: '{result_text}' for input: '{text}'")


class InterestingFactsExtractor:
    """Extract interesting linguistic facts from Dutch text with Russian explanations.

    This class analyzes Dutch text and provides detailed linguistic explanations in Russian.
    For single words, it gives lexical analysis with morphology, articles, and usage examples.
    For sentences, it provides word-by-word glosses plus sentence-level grammar notes.

    Only supports Dutch (NL) source language with Russian (RU) target explanations in V1.
    """

    def __init__(
        self,
        *,
        source_language: Language,
        target_language: Language,
        model: str = "gpt-4.1-mini",
        service_tier: str | None = "priority",
    ) -> None:
        """Initialize the facts extractor for a supported language pair.

        Args:
            source_language: Source language for input text (must be Language.NL)
            target_language: Target language for explanations (must be Language.RU)
            model: OpenAI model name (default: "gpt-4.1-mini")
            service_tier: OpenAI service tier (default: "priority")

        Raises:
            ValueError: If the language pair is not supported
        """
        pair = (source_language.value, target_language.value)
        if pair not in _SUPPORTED_PAIRS:
            supported = ", ".join("->".join(item) for item in sorted(_SUPPORTED_PAIRS))
            msg = f"Unsupported language pair {source_language.value}->{target_language.value}. Supported: {supported}"
            raise ValueError(msg)

        self._source_language = source_language
        self._target_language = target_language
        prompt = load_prompt(str(_PROMPTS_DIR / _PROMPT_FILE))
        llm_kwargs = build_llm_kwargs(
            model=model,
            service_tier=service_tier,
            reasoning_effort=None,
            temperature=None,
        )
        llm = ChatOpenAI(**llm_kwargs)
        self._chain: Runnable = prompt | llm

    async def extract(self, text: str) -> str:
        """Extract interesting linguistic facts from Dutch text.

        Analyzes the input text and returns Russian explanations with linguistic facts.
        For single words: detailed lexical analysis with morphology and usage.
        For sentences: word glosses plus sentence-level grammar notes.

        Args:
            text: Dutch text to analyze (must not be blank/whitespace-only)

        Returns:
            Russian explanation string with linguistic facts

        Raises:
            ValueError: If input text is blank or whitespace-only
            APIError: If model invocation fails or returns unusable content
        """
        if not text.strip():
            raise ValueError("Input text must not be blank or whitespace-only")

        try:
            response = await self._chain.ainvoke({"text": [HumanMessage(content=text)]})
            result_text: str = response.content
        except Exception as e:
            raise APIError(str(e)) from e

        _validate_response(result_text, text)
        return result_text
