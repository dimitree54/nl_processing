import pathlib

from langchain_core.messages import HumanMessage
from nl_processing.core.exceptions import APIError
from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.core.prompts import build_translation_chain
from pydantic import BaseModel

_PROMPTS_DIR = pathlib.Path(__file__).parent / "prompts"

_SUPPORTED_PAIRS: set[tuple[str, str]] = {("nl", "ru")}


class _LLMTranslationEntry(BaseModel):
    """Single translated word as returned by the LLM (no language field)."""

    normalized_form: str
    word_type: PartOfSpeech


class _TranslationBatch(BaseModel):
    """Internal wrapper: bind_tools needs a single model."""

    translations: list[_LLMTranslationEntry]


class WordTranslator:
    """Translate word batches between languages.

    Usage:
        translator = WordTranslator(
            source_language=Language.NL,
            target_language=Language.RU,
        )
        results = await translator.translate([Word(...), Word(...)])
    """

    def __init__(
        self,
        *,
        source_language: Language,
        target_language: Language,
        model: str = "gpt-5-mini",
        reasoning_effort: str | None = "medium",
        temperature: float | None = None,
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
            reasoning_effort=reasoning_effort,
            temperature=temperature,
        )

    async def translate(self, words: list[Word]) -> list[Word]:
        """Translate a list of Word objects from source to target language.

        Returns one Word per input word (in target language), in the same order.
        Returns empty list for empty input (no API call).
        """
        if not words:
            return []

        word_text = "\n".join(w.normalized_form for w in words)

        try:
            response = await self._chain.ainvoke({"text": [HumanMessage(content=word_text)]})
            result = _TranslationBatch(
                **response.tool_calls[0]["args"]  # type: ignore[attr-defined]
            )
        except Exception as e:
            raise APIError(str(e)) from e

        return [
            Word(
                normalized_form=entry.normalized_form,
                word_type=entry.word_type,
                language=self._target_language,
            )
            for entry in result.translations
        ]
