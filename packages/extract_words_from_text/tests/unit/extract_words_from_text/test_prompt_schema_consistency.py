"""Tests that the NL extraction prompt is consistent with the PartOfSpeech schema.

Bug #2: The prompt instructs the LLM to extract phraseological units, but
PartOfSpeech has no 'phrase' value — so the LLM can return 'phrase' as
word_type, which fails Pydantic validation and raises APIError in production.

These tests are written to assert the *correct* contract and therefore FAIL
on the current codebase, reproducing the bug.
"""

import pytest

from nl_processing.core.models import PartOfSpeech
from nl_processing.extract_words_from_text.prompts.generate_nl_prompt import (
    EXAMPLES,
    SYSTEM_INSTRUCTION,
)
from nl_processing.extract_words_from_text.service import (
    WordExtractor,
    _WordList,
)
from tests.unit.extract_words_from_text.conftest import (
    _AsyncChainMock,
    make_tool_response,
)


def _prompt_allowed_types() -> set[str]:
    """Extract the word_type values listed in the prompt text."""
    marker = "Mogelijke types: "
    idx = SYSTEM_INSTRUCTION.index(marker)
    rest = SYSTEM_INSTRUCTION[idx + len(marker) :]
    types_str = rest.split(".")[0]
    return {t.strip() for t in types_str.split(",")}


def _enum_values() -> set[str]:
    return {pos.value for pos in PartOfSpeech}


class TestPromptSchemaContract:
    """The prompt must not instruct behavior that the schema cannot represent.

    If the prompt tells the LLM to extract phraseological constructions,
    there must be a valid word_type in PartOfSpeech to classify them.
    Otherwise the LLM will invent 'phrase' and validation will fail.
    """

    def test_phrase_extraction_instruction_has_matching_type(self) -> None:
        """FAILS: Prompt asks for phraseological units but no 'phrase' type exists.

        The prompt says: "Extraheer samengestelde uitdrukkingen en
        fraseologische constructies als enkele eenheden."

        This instruction will cause the LLM to return entries that don't
        fit standard POS categories. The prompt MUST either:
        - Remove the phraseological extraction instruction, OR
        - Add 'phrase' to the allowed types list AND to PartOfSpeech enum.

        Current state: instruction present, 'phrase' absent → FAIL.
        """
        instructs_phrase_extraction = "fraseologische constructies" in SYSTEM_INSTRUCTION
        has_phrase_type = "phrase" in _enum_values()
        prompt_lists_phrase = "phrase" in _prompt_allowed_types()

        # If the prompt instructs phraseological extraction,
        # there must be a 'phrase' type in both the prompt list AND the enum
        if instructs_phrase_extraction:
            assert has_phrase_type, (
                "PartOfSpeech enum is missing 'phrase' but the prompt instructs "
                "extraction of phraseological constructions. The LLM will return "
                "'phrase' as word_type, causing ValidationError."
            )
            assert prompt_lists_phrase, (
                "Prompt 'Mogelijke types' list is missing 'phrase' but the prompt "
                "instructs extraction of phraseological constructions."
            )

    def test_every_few_shot_word_type_is_valid_pos(self) -> None:
        """All word_type values in few-shot examples must be valid PartOfSpeech values."""
        enum_values = _enum_values()
        for i, (text, words) in enumerate(EXAMPLES, 1):
            for w in words:
                assert w["word_type"] in enum_values, (
                    f"Example {i} ({text!r}): word_type {w['word_type']!r} is not a valid PartOfSpeech value"
                )


class TestPhraseTypeServicePath:
    """Simulate the production failure: LLM returns word_type='phrase'.

    This demonstrates that the current service CANNOT handle the output
    its own prompt encourages.
    """

    @pytest.mark.asyncio
    async def test_extract_succeeds_with_phrase_type(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """FAILS: Service should accept 'phrase' but PartOfSpeech rejects it.

        In production, when the LLM follows the prompt instruction to
        extract phraseological constructions, it returns word_type='phrase'.
        The service should handle this gracefully, but instead it raises
        APIError due to Pydantic validation failure.
        """
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        # This is what the LLM actually returns in production when
        # encountering phraseological units like "op het eerste gezicht"
        words_data = [
            {"normalized_form": "de kat", "word_type": "noun"},
            {"normalized_form": "lopen", "word_type": "verb"},
            {"normalized_form": "op het eerste gezicht", "word_type": "phrase"},
        ]

        extractor = WordExtractor()
        extractor._chain = _AsyncChainMock(make_tool_response(words_data))

        # This SHOULD succeed — the prompt encourages this output
        result = await extractor.extract("De kat loopt op het eerste gezicht snel.")
        assert len(result) == 3
        assert result[2].normalized_form == "op het eerste gezicht"

    def test_word_list_accepts_phrase_type(self) -> None:
        """FAILS: _WordList should parse 'phrase' as a valid word_type.

        The prompt instructs phrase extraction, so the schema must support it.
        """
        word_list = _WordList(
            words=[
                {"normalized_form": "de kat", "word_type": "noun"},
                {"normalized_form": "op het eerste gezicht", "word_type": "phrase"},
            ]
        )
        assert len(word_list.words) == 2
