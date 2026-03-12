import pathlib

from langchain_core.messages import HumanMessage
from nl_processing.core.exceptions import APIError
from nl_processing.core.models import Language
from nl_processing.core.prompts import build_bidirectional_translation_chain
from pydantic import BaseModel

_PROMPTS_DIR = pathlib.Path(__file__).parent / "prompts"
_PROMPT_FILE = "nl_ru_bidirectional.json"
_SUPPORTED_PAIRS: set[frozenset[str]] = {frozenset({"nl", "ru"})}


class _NlToRuTranslation(BaseModel):
    text: str


class _RuToNlTranslation(BaseModel):
    text: str


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
