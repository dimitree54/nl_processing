import pathlib

from langchain_core.messages import HumanMessage
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from nl_processing.core.exceptions import APIError
from nl_processing.core.models import Language
from nl_processing.core.prompts import build_llm_kwargs, load_prompt
from pydantic import BaseModel

_PROMPTS_DIR = pathlib.Path(__file__).parent / "prompts"
_PROMPT_FILE = "nl_ru_bidirectional.json"
_SUPPORTED_PAIRS: set[frozenset[str]] = {frozenset({"nl", "ru"})}


class _NlToRuTranslation(BaseModel):
    text: str


class _RuToNlTranslation(BaseModel):
    text: str


def build_bidirectional_translation_chain(
    *,
    language_a: Language,
    language_b: Language,
    supported_pairs: set[frozenset[str]],
    prompts_dir: pathlib.Path,
    prompt_file: str,
    tool_schemas: list[type[BaseModel]],
    model: str,
    service_tier: str | None = None,
    reasoning_effort: str | None = None,
    temperature: float | None = None,
) -> Runnable:
    pair = frozenset({language_a.value, language_b.value})
    if pair not in supported_pairs:
        supported = ", ".join(
            "<->".join(sorted(item)) for item in sorted(supported_pairs, key=lambda item: tuple(sorted(item)))
        )
        msg = f"Unsupported language pair {language_a.value}->{language_b.value}. Supported: {supported}"
        raise ValueError(msg)

    prompt = load_prompt(str(prompts_dir / prompt_file))
    llm_kwargs = build_llm_kwargs(
        model=model,
        service_tier=service_tier,
        reasoning_effort=reasoning_effort,
        temperature=temperature,
    )
    llm = ChatOpenAI(**llm_kwargs).bind_tools(tool_schemas)
    return prompt | llm


class BidirectionalTextTranslator:
    """Translate text bidirectionally between Dutch and Russian.

    Usage:
        translator = BidirectionalTextTranslator(
            source_language=Language.NL,
            target_language=Language.RU,
        )
        result = await translator.translate(dutch_or_russian_text)
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
            language_a=source_language,
            language_b=target_language,
            supported_pairs=_SUPPORTED_PAIRS,
            prompts_dir=_PROMPTS_DIR,
            prompt_file=_PROMPT_FILE,
            tool_schemas=[_NlToRuTranslation, _RuToNlTranslation],
            model=model,
            service_tier=service_tier,
        )

    async def translate(self, text: str) -> str:
        """Translate text, inferring direction from input language.

        Returns the translated text or empty string for empty/non-supported input.
        """
        if not text.strip():
            return ""

        try:
            response = await self._chain.ainvoke({"text": [HumanMessage(content=text)]})
            result_text = response.tool_calls[0]["args"]["text"]  # type: ignore[attr-defined]
        except Exception as e:
            raise APIError(str(e)) from e

        return result_text
