import pathlib

from langchain_core.messages import HumanMessage
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from nl_processing.core.exceptions import APIError
from nl_processing.core.models import Language
from nl_processing.core.prompts import build_llm_kwargs
from pydantic import BaseModel

from nl_processing.translate_text_bidirectional.prompts.generate_nl_ru_bidirectional_prompt import (
    build_dynamic_prompt,
)

_PROMPTS_DIR = pathlib.Path(__file__).parent / "prompts"
_PROMPT_FILE = "nl_ru_bidirectional.json"
_SUPPORTED_PAIRS: set[frozenset[str]] = {frozenset({"nl", "ru"})}


class _NlToRuTranslation(BaseModel):
    text: str


class _RuToNlTranslation(BaseModel):
    text: str


def build_bidirectional_translation_chain(
    *,
    source_language: Language,
    target_language: Language,
    supported_pairs: set[frozenset[str]],
    tool_schemas: list[type[BaseModel]],
    model: str,
    service_tier: str | None = None,
    reasoning_effort: str | None = None,
    temperature: float | None = None,
) -> Runnable:
    pair = frozenset({source_language.value, target_language.value})
    if pair not in supported_pairs:
        supported = ", ".join(
            "<->".join(sorted(item)) for item in sorted(supported_pairs, key=lambda item: tuple(sorted(item)))
        )
        msg = f"Unsupported language pair {source_language.value}->{target_language.value}. Supported: {supported}"
        raise ValueError(msg)

    prompt = build_dynamic_prompt(source_language=source_language, target_language=target_language)
    llm_kwargs = build_llm_kwargs(
        model=model,
        service_tier=service_tier,
        reasoning_effort=reasoning_effort,
        temperature=temperature,
    )
    llm = ChatOpenAI(**llm_kwargs).bind_tools(tool_schemas)
    return prompt | llm


class BidirectionalTextTranslator:
    """Translate text bidirectionally between Dutch and Russian using source-anchored semantics.

    Source-anchored behavior:
    - Input in the configured source_language is translated to target_language
    - Input not in the configured source_language is translated to source_language

    Constructor parameter order is semantically meaningful:
    - BidirectionalTextTranslator(source=Language.NL, target=Language.RU)
    - BidirectionalTextTranslator(source=Language.RU, target=Language.NL)

    Usage:
        translator = BidirectionalTextTranslator(
            source_language=Language.NL,
            target_language=Language.RU,
        )
        # Dutch input -> Russian output
        # Russian/English/other input -> Dutch output
        result = await translator.translate(text)
    """

    def __init__(
        self,
        *,
        source_language: Language,
        target_language: Language,
        model: str = "gpt-4.1-mini",
        service_tier: str | None = "priority",
    ) -> None:
        self._source_language = source_language
        self._target_language = target_language
        self._chain = build_bidirectional_translation_chain(
            source_language=source_language,
            target_language=target_language,
            supported_pairs=_SUPPORTED_PAIRS,
            tool_schemas=[_NlToRuTranslation, _RuToNlTranslation],
            model=model,
            service_tier=service_tier,
        )

    async def translate(self, text: str) -> str:
        """Translate text using source-anchored semantics.

        If input is in the configured source_language, translates to target_language.
        If input is not in the configured source_language, translates to source_language.
        Returns empty string only for blank/whitespace input.
        """
        if not text.strip():
            return ""

        try:
            response = await self._chain.ainvoke({"text": [HumanMessage(content=text)]})
            result_text = self._extract_translation_from_response(response)
        except Exception as e:
            raise APIError(str(e)) from e

        return result_text

    def _extract_translation_from_response(self, response: object) -> str:
        """Extract translation text from LLM response with robust error handling."""
        # Validate response has tool_calls attribute
        try:
            tool_calls = response.tool_calls
        except AttributeError:
            msg = "LLM response missing tool_calls attribute"
            raise APIError(msg) from None

        # Validate tool_calls is not empty
        if not tool_calls:
            msg = "LLM response contains no tool calls"
            raise APIError(msg)

        # Validate first tool call has required structure
        tool_call = tool_calls[0]
        if not isinstance(tool_call, dict):
            msg = f"Tool call is not a dictionary: {type(tool_call)}"
            raise APIError(msg)

        # Validate tool call has args
        if "args" not in tool_call:
            msg = "Tool call missing 'args' field"
            raise APIError(msg)

        args = tool_call["args"]
        if not isinstance(args, dict):
            msg = f"Tool call args is not a dictionary: {type(args)}"
            raise APIError(msg)

        # Validate args has text field
        if "text" not in args:
            msg = "Tool call args missing 'text' field"
            raise APIError(msg)

        result_text = args["text"]
        if not isinstance(result_text, str):
            msg = f"Tool call args.text is not a string: {type(result_text)}"
            raise APIError(msg)

        return result_text
