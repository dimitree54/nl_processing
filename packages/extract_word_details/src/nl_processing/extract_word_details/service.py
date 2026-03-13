"""WordDetailsExtractor service for extracting detailed linguistic information."""

import pathlib

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableSerializable
from langchain_openai import ChatOpenAI
from nl_processing.core.exceptions import APIError
from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.core.prompts import load_prompt
from nl_processing.database.detailed_models import DetailedWordRecord

from nl_processing.extract_word_details._pos_config import POS_CONFIG
from nl_processing.extract_word_details._pos_dispatch import (
    get_supported_pos,
    group_words_by_pos,
    split_supported_unsupported,
)
from nl_processing.extract_word_details._serializer import serialize_payload
from nl_processing.extract_word_details.logging import get_logger

_PROMPTS_DIR = pathlib.Path(__file__).parent / "prompts"
_SUPPORTED_PAIRS: set[tuple[str, str]] = {("nl", "ru")}

_logger = get_logger("service")


class WordDetailsExtractor:
    """Extract detailed linguistic information for Dutch words with Russian explanations.

    Usage:
        extractor = WordDetailsExtractor(
            source_language=Language.NL,
            target_language=Language.RU,
        )
        results = await extractor.extract([Word(...), Word(...)])
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
        """Initialize the word details extractor.

        Args:
            source_language: Source language for words to extract details from
            target_language: Target language for explanations
            model: OpenAI model to use for extraction
            reasoning_effort: Reasoning effort for the model
            temperature: Temperature setting for the model

        Raises:
            ValueError: If language pair is not supported
        """
        self._source_language = source_language
        self._target_language = target_language

        # Validate supported language pair
        language_pair = (source_language.value, target_language.value)
        if language_pair not in _SUPPORTED_PAIRS:
            raise ValueError(f"Unsupported language pair: {language_pair}")

        self._supported_pos = get_supported_pos()
        self._chains: dict[PartOfSpeech, RunnableSerializable] = {}

        # Build chains for each supported POS
        for pos in self._supported_pos:
            if pos in POS_CONFIG:
                config = POS_CONFIG[pos]
                prompt_path = _PROMPTS_DIR / config["prompt_file"]

                # Load the prompt and build the chain manually
                prompt = load_prompt(str(prompt_path))
                llm = ChatOpenAI(
                    model=model,
                    temperature=temperature,
                    reasoning_effort=reasoning_effort,
                ).bind_tools(
                    [config["batch_model"]],
                    tool_choice=config["batch_model"].__name__,
                )
                self._chains[pos] = prompt | llm

    async def extract(self, words: list[Word]) -> list[DetailedWordRecord]:
        """Extract detailed information for a list of words.

        Args:
            words: List of words to extract details for

        Returns:
            List of DetailedWordRecord objects with detailed information,
            in the same order as supported input words

        Raises:
            ValueError: If words have mixed languages
            APIError: If LLM call fails or returns malformed output
        """
        if not words:
            return []

        # Validate single language
        if not all(word.language == self._source_language for word in words):
            raise ValueError("All words must have the same language")

        # Split supported and unsupported words
        supported_words, unsupported_words = split_supported_unsupported(words, self._supported_pos)

        # Log warnings for unsupported words
        for index, word in unsupported_words:
            _logger.warning("Skipping unsupported POS: word='%s' pos='%s'", word.normalized_form, word.word_type.value)

        if not supported_words:
            return []

        # Group supported words by POS
        pos_groups = group_words_by_pos([word for _, word in supported_words])

        # Extract details for each POS group
        all_results: list[tuple[int, DetailedWordRecord]] = []

        for pos, indexed_words in pos_groups.items():
            if pos not in self._chains:
                continue

            config = POS_CONFIG[pos]
            chain = self._chains[pos]

            # Build input text from normalized forms
            words_for_extraction = [word for _, word in indexed_words]
            word_text = "\n".join(w.normalized_form for w in words_for_extraction)

            try:
                response = await chain.ainvoke({"text": [HumanMessage(content=word_text)]})

                if not response.tool_calls:
                    raise APIError("LLM returned empty tool_calls")

                batch_result = config["batch_model"](**response.tool_calls[0]["args"])

                # Validate we got the expected number of results
                if len(batch_result.details) != len(words_for_extraction):
                    raise APIError(f"Expected {len(words_for_extraction)} results, got {len(batch_result.details)}")

                # Create DetailedWordRecord for each result
                for (original_index, word), detail_model in zip(indexed_words, batch_result.details):
                    payload = serialize_payload(detail_model)

                    record = DetailedWordRecord(
                        source_word=word.normalized_form,
                        word_type=word.word_type.value,
                        schema_key=config["schema_key"],
                        schema_version=config["schema_version"],
                        payload=payload,
                    )

                    all_results.append((original_index, record))

            except Exception as e:
                raise APIError(str(e)) from e

        # Sort results by original index to maintain input order
        all_results.sort(key=lambda x: x[0])

        return [record for _, record in all_results]
