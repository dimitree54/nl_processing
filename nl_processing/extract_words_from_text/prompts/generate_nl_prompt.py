"""Generate the Dutch word extraction prompt (nl.json) with few-shot examples.

Usage:
    uv run python nl_processing/extract_words_from_text/prompts/generate_nl_prompt.py

This script:
1. Defines a system instruction for Dutch word extraction and normalization
2. Builds few-shot examples as HumanMessage + AIMessage(tool_calls) + ToolMessage triplets
3. Serializes with dumpd() and saves to nl.json

The script is the source of truth -- nl.json is the generated artifact.
Re-run this script whenever prompt content changes.
"""

import json
from pathlib import Path

from langchain_core.load import dumpd
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

SYSTEM_INSTRUCTION = (
    "Je bent een woord-extractie assistent voor de Nederlandse taal. "
    "Je taak is om alle Nederlandse woorden uit de aangeboden tekst te extraheren en te normaliseren.\n\n"
    "Regels:\n"
    "- Negeer alle markdown-opmaak (koppen, vet, cursief, lijsten) -- extraheer alleen taalkundige inhoud.\n"
    "- Negeer tekst in andere talen dan Nederlands.\n"
    "- Normaliseer elk woord volgens de Nederlandse regels:\n"
    "  - Zelfstandige naamwoorden: met lidwoord (de/het), bijv. 'de fiets', 'het huis'\n"
    "  - Werkwoorden: infinitief, bijv. 'lopen', 'hebben'\n"
    "  - Bijvoeglijke naamwoorden: basisvorm, bijv. 'groot', 'klein'\n"
    "  - Voorzetsels, voegwoorden, bijwoorden: basisvorm\n"
    "  - Eigennamen (personen): ongewijzigd, type 'proper_noun_person'\n"
    "  - Eigennamen (landen): ongewijzigd, type 'proper_noun_country'\n"
    "- Extraheer samengestelde uitdrukkingen en fraseologische constructies als enkele eenheden.\n"
    "- Wijs een plat woordtype toe aan elk woord. Mogelijke types: "
    "noun, verb, adjective, adverb, preposition, conjunction, pronoun, article, numeral, "
    "proper_noun_person, proper_noun_country.\n"
    "- Retourneer het resultaat als een lijst van WordEntry objecten in een _WordList wrapper.\n"
    "- Als de tekst geen Nederlandse woorden bevat, retourneer dan een lege lijst."
)

TOOL_NAME = "_WordList"

OUTPUT_PATH = Path(__file__).parent / "nl.json"


def _make_ai_response(words: list[dict[str, str]], call_id: str) -> AIMessage:
    """Create an AIMessage with tool_calls for _WordList."""
    return AIMessage(
        content="",
        tool_calls=[{"name": TOOL_NAME, "args": {"words": words}, "id": call_id}],
    )


def _make_tool_ack(words: list[dict[str, str]], call_id: str) -> ToolMessage:
    """Create a ToolMessage acknowledging the tool call."""
    return ToolMessage(content=json.dumps({"words": words}, ensure_ascii=False), tool_call_id=call_id)


def build_prompt() -> ChatPromptTemplate:
    """Build the Dutch word extraction prompt with few-shot examples."""
    # Example 1: Simple sentence with noun (de/het), verb, adjective
    ex1_input = "De grote kat loopt snel."
    ex1_words = [
        {"normalized_form": "de kat", "word_type": "noun"},
        {"normalized_form": "groot", "word_type": "adjective"},
        {"normalized_form": "lopen", "word_type": "verb"},
        {"normalized_form": "snel", "word_type": "adverb"},
    ]

    # Example 2: Proper nouns and prepositions
    ex2_input = "Jan woont in Nederland."
    ex2_words = [
        {"normalized_form": "Jan", "word_type": "proper_noun_person"},
        {"normalized_form": "wonen", "word_type": "verb"},
        {"normalized_form": "in", "word_type": "preposition"},
        {"normalized_form": "Nederland", "word_type": "proper_noun_country"},
    ]

    # Example 3: Compound expression
    ex3_input = "Zij gaat er vandoor met haar vriend."
    ex3_words = [
        {"normalized_form": "zij", "word_type": "pronoun"},
        {"normalized_form": "ervandoor gaan", "word_type": "verb"},
        {"normalized_form": "met", "word_type": "preposition"},
        {"normalized_form": "haar", "word_type": "pronoun"},
        {"normalized_form": "de vriend", "word_type": "noun"},
    ]

    # Example 4: Non-Dutch text -- returns empty list
    ex4_input = "The quick brown fox jumps over the lazy dog."
    ex4_words: list[dict[str, str]] = []

    # Example 5: Mixed markdown with various word types
    ex5_input = "# Welkom\n\nHet **kleine** kind speelt vrolijk in de tuin."
    ex5_words = [
        {"normalized_form": "welkom", "word_type": "adjective"},
        {"normalized_form": "het kind", "word_type": "noun"},
        {"normalized_form": "klein", "word_type": "adjective"},
        {"normalized_form": "spelen", "word_type": "verb"},
        {"normalized_form": "vrolijk", "word_type": "adverb"},
        {"normalized_form": "in", "word_type": "preposition"},
        {"normalized_form": "de tuin", "word_type": "noun"},
    ]

    return ChatPromptTemplate.from_messages([
        SystemMessage(content=SYSTEM_INSTRUCTION),
        # Example 1
        HumanMessage(content=ex1_input),
        _make_ai_response(ex1_words, "call_ex_1"),
        _make_tool_ack(ex1_words, "call_ex_1"),
        # Example 2
        HumanMessage(content=ex2_input),
        _make_ai_response(ex2_words, "call_ex_2"),
        _make_tool_ack(ex2_words, "call_ex_2"),
        # Example 3
        HumanMessage(content=ex3_input),
        _make_ai_response(ex3_words, "call_ex_3"),
        _make_tool_ack(ex3_words, "call_ex_3"),
        # Example 4
        HumanMessage(content=ex4_input),
        _make_ai_response(ex4_words, "call_ex_4"),
        _make_tool_ack(ex4_words, "call_ex_4"),
        # Example 5
        HumanMessage(content=ex5_input),
        _make_ai_response(ex5_words, "call_ex_5"),
        _make_tool_ack(ex5_words, "call_ex_5"),
        # Placeholder for actual user input
        MessagesPlaceholder(variable_name="text"),
    ])


if __name__ == "__main__":
    prompt = build_prompt()
    data = dumpd(prompt)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print(f"Prompt saved to {OUTPUT_PATH}")  # noqa: T201
    print(f"Messages: {len(prompt.messages)}")  # noqa: T201
    print(f"Input variables: {prompt.input_variables}")  # noqa: T201
