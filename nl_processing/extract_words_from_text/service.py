import pathlib

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from nl_processing.core.exceptions import APIError
from nl_processing.core.models import Language, WordEntry
from nl_processing.core.prompts import load_prompt

# Resolve prompts directory relative to this file
_PROMPTS_DIR = pathlib.Path(__file__).parent / "prompts"


class _WordList(BaseModel):
    """Internal wrapper: bind_tools needs a single model, output is a list."""

    words: list[WordEntry]


class WordExtractor:
    """Extract and normalize words from markdown text.

    Usage:
        extractor = WordExtractor()
        words = await extractor.extract(text)
    """

    def __init__(
        self,
        *,
        language: Language = Language.NL,
        model: str = "gpt-4.1-mini",
    ) -> None:
        self._language = language
        prompt_path = str(_PROMPTS_DIR / f"{language.value}.json")
        prompt = load_prompt(prompt_path)

        llm = ChatOpenAI(model=model, temperature=0).bind_tools([_WordList], tool_choice=_WordList.__name__)
        self._chain = prompt | llm

    async def extract(self, text: str) -> list[WordEntry]:
        """Extract and normalize words from the given text.

        Returns a list of WordEntry objects with normalized forms and types.
        Returns an empty list if no words in the target language are found.
        """
        try:
            response = await self._chain.ainvoke({"text": [HumanMessage(content=text)]})
            result = _WordList(**response.tool_calls[0]["args"])  # type: ignore[attr-defined]
        except Exception as e:
            raise APIError(str(e)) from e

        return result.words
