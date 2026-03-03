import pathlib

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from nl_processing.core.exceptions import APIError
from nl_processing.core.models import Language
from nl_processing.core.prompts import load_prompt

_PROMPTS_DIR = pathlib.Path(__file__).parent / "prompts"

_SUPPORTED_PAIRS: set[tuple[str, str]] = {("nl", "ru")}


class _TranslatedText(BaseModel):
    text: str


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
    ) -> None:
        pair = (source_language.value, target_language.value)
        if pair not in _SUPPORTED_PAIRS:
            msg = (
                f"Unsupported language pair: "
                f"{source_language.value} -> {target_language.value}. "
                f"Supported pairs: {_SUPPORTED_PAIRS}"
            )
            raise ValueError(msg)

        self._source_language = source_language
        self._target_language = target_language

        prompt_file = f"{source_language.value}_{target_language.value}.json"
        prompt_path = str(_PROMPTS_DIR / prompt_file)
        prompt = load_prompt(prompt_path)

        llm = ChatOpenAI(model=model, temperature=0).bind_tools([_TranslatedText], tool_choice=_TranslatedText.__name__)
        self._chain = prompt | llm

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
