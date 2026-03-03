import pathlib

from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from nl_processing.core.exceptions import APIError
from nl_processing.core.models import Language, TranslationResult
from nl_processing.core.prompts import build_translation_chain

_PROMPTS_DIR = pathlib.Path(__file__).parent / "prompts"

_SUPPORTED_PAIRS: set[tuple[str, str]] = {("nl", "ru")}


class _TranslationBatch(BaseModel):
    translations: list[TranslationResult]


class WordTranslator:
    """Translate word batches between languages.

    Usage:
        translator = WordTranslator(
            source_language=Language.NL,
            target_language=Language.RU,
        )
        results = await translator.translate(["huis", "lopen"])
    """

    def __init__(
        self,
        *,
        source_language: Language,
        target_language: Language,
        model: str = "gpt-4.1-mini",
    ) -> None:
        self._source_language = source_language
        self._target_language = target_language
        self._chain = build_translation_chain(
            source_language=source_language,
            target_language=target_language,
            supported_pairs=_SUPPORTED_PAIRS,
            prompts_dir=_PROMPTS_DIR,
            tool_schema=_TranslationBatch,
            model=model,
        )

    async def translate(self, words: list[str]) -> list[TranslationResult]:
        """Translate a list of words from source to target language.

        Returns one TranslationResult per input word, in the same order.
        Returns empty list for empty input (no API call).
        """
        if not words:
            return []

        word_text = "\n".join(words)

        try:
            response = await self._chain.ainvoke({"text": [HumanMessage(content=word_text)]})
            result = _TranslationBatch(
                **response.tool_calls[0]["args"]  # type: ignore[attr-defined]
            )
        except Exception as e:
            raise APIError(str(e)) from e

        return result.translations
