"""Generate the Dutch-to-Russian word translation prompt (nl_ru.json).

Usage:
    uv run python nl_processing/translate_word/prompts/generate_nl_ru_prompt.py

This script:
1. Builds a ChatPromptTemplate with system instruction and 4 few-shot examples
2. Demonstrates one-to-one order-preserving word translation
3. Serializes with dumpd() and saves to nl_ru.json

The script is the source of truth -- nl_ru.json is the generated artifact.
Re-run this script whenever prompt content changes.
"""

import json
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

SYSTEM_INSTRUCTION = (
    "Вы — профессиональный переводчик с нидерландского языка на русский. "
    "Вы получаете список нидерландских слов или фраз и должны перевести каждое на русский. "
    "Верните ровно один перевод для каждого входного слова, в том же порядке. "
    "Количество переводов в результате должно равняться количеству слов на входе. "
    "Каждый перевод должен содержать нормализованную форму слова на русском языке "
    "и часть речи (word_type). "
    "Возможные значения word_type: noun, verb, adjective, adverb, preposition, "
    "conjunction, pronoun, article, numeral, proper_noun_person, proper_noun_country. "
    "Если входной список пуст, верните пустой список."
)

EXAMPLE_1_INPUT = "huis\nlopen\nsnel"
EXAMPLE_1_OUTPUT = [
    {"normalized_form": "дом", "word_type": "noun"},
    {"normalized_form": "ходить", "word_type": "verb"},
    {"normalized_form": "быстро", "word_type": "adverb"},
]

EXAMPLE_2_INPUT = "de kat\nhet boek\nschrijven\nmooi\nin"
EXAMPLE_2_OUTPUT = [
    {"normalized_form": "кошка", "word_type": "noun"},
    {"normalized_form": "книга", "word_type": "noun"},
    {"normalized_form": "писать", "word_type": "verb"},
    {"normalized_form": "красивый", "word_type": "adjective"},
    {"normalized_form": "в", "word_type": "preposition"},
]

EXAMPLE_3_INPUT = "er vandoor gaan\nde fiets"
EXAMPLE_3_OUTPUT = [
    {"normalized_form": "сбежать", "word_type": "verb"},
    {"normalized_form": "велосипед", "word_type": "noun"},
]

EXAMPLE_4_INPUT = ""
EXAMPLE_4_OUTPUT: list[dict[str, str]] = []

OUTPUT_PATH = Path(__file__).parent / "nl_ru.json"


def _make_example_ai(translations: list[dict[str, str]], call_id: str) -> AIMessage:
    """Create an AIMessage with a tool_call for _TranslationBatch."""
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "_TranslationBatch",
                "args": {"translations": translations},
                "id": call_id,
            }
        ],
    )


def build_prompt() -> ChatPromptTemplate:
    """Build the Dutch-to-Russian word translation prompt with few-shot examples."""
    return ChatPromptTemplate.from_messages([
        SystemMessage(content=SYSTEM_INSTRUCTION),
        # Example 1: 3 simple words
        HumanMessage(content=EXAMPLE_1_INPUT),
        _make_example_ai(EXAMPLE_1_OUTPUT, "call_example_1"),
        ToolMessage(
            content=json.dumps({"translations": EXAMPLE_1_OUTPUT}, ensure_ascii=False),
            tool_call_id="call_example_1",
        ),
        # Example 2: 5 words with articles
        HumanMessage(content=EXAMPLE_2_INPUT),
        _make_example_ai(EXAMPLE_2_OUTPUT, "call_example_2"),
        ToolMessage(
            content=json.dumps({"translations": EXAMPLE_2_OUTPUT}, ensure_ascii=False),
            tool_call_id="call_example_2",
        ),
        # Example 3: compound expression
        HumanMessage(content=EXAMPLE_3_INPUT),
        _make_example_ai(EXAMPLE_3_OUTPUT, "call_example_3"),
        ToolMessage(
            content=json.dumps({"translations": EXAMPLE_3_OUTPUT}, ensure_ascii=False),
            tool_call_id="call_example_3",
        ),
        # Example 4: empty list
        HumanMessage(content=EXAMPLE_4_INPUT),
        _make_example_ai(EXAMPLE_4_OUTPUT, "call_example_4"),
        ToolMessage(
            content=json.dumps({"translations": EXAMPLE_4_OUTPUT}, ensure_ascii=False),
            tool_call_id="call_example_4",
        ),
        # Placeholder for actual input
        MessagesPlaceholder(variable_name="text"),
    ])


if __name__ == "__main__":
    from nl_processing.core.scripts.prompt_author import save_prompt

    save_prompt(build_prompt(), str(OUTPUT_PATH))
