import pathlib

from langchain_core.messages import HumanMessage
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from nl_processing.core.exceptions import APIError
from nl_processing.core.models import Language
from nl_processing.core.prompts import build_llm_kwargs, load_prompt
from pydantic import BaseModel

_PROMPTS_DIR = pathlib.Path(__file__).parent / "prompts"

_SUPPORTED_PAIRS: set[tuple[str, str]] = {("nl", "ru")}


class _TranslatedText(BaseModel):
    text: str


def _build_translation_chain(
    *,
    source_language: Language,
    target_language: Language,
    supported_pairs: set[tuple[str, str]],
    prompts_dir: pathlib.Path,
    tool_schema: type[BaseModel],
    model: str,
    service_tier: str | None = None,
    reasoning_effort: str | None = None,
    temperature: float | None = None,
) -> Runnable:
    pair = (source_language.value, target_language.value)
    if pair not in supported_pairs:
        supported = ", ".join(f"{src}->{target}" for src, target in sorted(supported_pairs))
        msg = f"Unsupported language pair {pair[0]}->{pair[1]}. Supported: {supported}"
        raise ValueError(msg)

    prompt = load_prompt(str(prompts_dir / f"{pair[0]}_{pair[1]}.json"))
    llm_kwargs = build_llm_kwargs(
        model=model,
        service_tier=service_tier,
        reasoning_effort=reasoning_effort,
        temperature=temperature,
    )
    llm = ChatOpenAI(**llm_kwargs).bind_tools([tool_schema], tool_choice=tool_schema.__name__)
    return prompt | llm


class TextTranslator:
    """Translate text between languages with markdown preservation.

    Usage:
        translator = TextTranslator(
            source_language=Language.NL,
            target_language=Language.RU,
        )
        result = await translator.translate(dutch_text)
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
        self._chain = _build_translation_chain(
            source_language=source_language,
            target_language=target_language,
            supported_pairs=_SUPPORTED_PAIRS,
            prompts_dir=_PROMPTS_DIR,
            tool_schema=_TranslatedText,
            model=model,
            service_tier=service_tier,
        )

    async def translate(self, text: str) -> str:
        """Translate text from source to target language.

        Returns the translated text or empty string for empty/non-source input.
        """
        if not text.strip():
            return ""

        try:
            response = await self._chain.ainvoke({"text": [HumanMessage(content=text)]})
            result = _TranslatedText(
                **response.tool_calls[0]["args"]  # type: ignore[attr-defined]
            )
        except Exception as e:
            raise APIError(str(e)) from e

        return result.text
