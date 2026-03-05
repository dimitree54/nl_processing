"""Generate the Dutch word extraction prompt (nl.json) with few-shot examples.

Usage:
    uv run python nl_processing/extract_words_from_text/prompts/generate_nl_prompt.py

The script is the source of truth -- nl.json is the generated artifact.
Re-run this script whenever prompt content changes.
"""

import json
from pathlib import Path

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
    "  - Eigennamen (personen/merken): ongewijzigd, type 'proper_noun_person'\n"
    "  - Eigennamen (landen): ongewijzigd, type 'proper_noun_country'\n"
    "- Extraheer samengestelde uitdrukkingen en fraseologische constructies als enkele eenheden.\n"
    "- Wijs een plat woordtype toe aan elk woord. Mogelijke types: "
    "noun, verb, adjective, adverb, preposition, conjunction, pronoun, article, numeral, "
    "interjection, "
    "proper_noun_person, proper_noun_country.\n"
    "- Retourneer het resultaat als een lijst van woord-objecten in een _WordList wrapper.\n"
    "- Als de tekst geen Nederlandse woorden bevat, retourneer dan een lege lijst."
)

TOOL_NAME = "_WordList"
OUTPUT_PATH = Path(__file__).parent / "nl.json"

_W = dict[str, str]


def _w(form: str, wtype: str) -> _W:
    return {"normalized_form": form, "word_type": wtype}


# fmt: off
EXAMPLES: list[tuple[str, list[_W]]] = [
    # 1: Simple sentence — noun (de/het), verb, adjective
    ("De grote kat loopt snel.", [
        _w("de kat", "noun"), _w("groot", "adjective"),
        _w("lopen", "verb"), _w("snel", "adverb"),
    ]),
    # 2: Proper nouns and prepositions
    ("Jan woont in Nederland.", [
        _w("Jan", "proper_noun_person"), _w("wonen", "verb"),
        _w("in", "preposition"), _w("Nederland", "proper_noun_country"),
    ]),
    # 3: Compound expression
    ("Zij gaat er vandoor met haar vriend.", [
        _w("zij", "pronoun"), _w("ervandoor gaan", "verb"),
        _w("met", "preposition"), _w("haar", "pronoun"), _w("de vriend", "noun"),
    ]),
    # 4: Non-Dutch text — empty list
    ("The quick brown fox jumps over the lazy dog.", []),
    # 5: Mixed markdown with various word types
    ("# Welkom\n\nHet **kleine** kind speelt vrolijk in de tuin.", [
        _w("welkom", "adjective"), _w("het kind", "noun"), _w("klein", "adjective"),
        _w("spelen", "verb"), _w("vrolijk", "adverb"),
        _w("in", "preposition"), _w("de tuin", "noun"),
    ]),
    # 6: Product packaging prose — brand names, adjectives as base form, plurals singularized
    (
        "Met De Ruijter kunt u elke dag genieten "
        "van een breed assortiment smakelijke producten.\n"
        "Chocoladevlokken Melk en Puur\n"
        "Chocoladehagel Melk en Puur\n"
        "Vruchtenhagel\nAnijshagel\nVlokfeest\n"
        "Gestampte Muisjes\nRose en Witte Muisjes\nBlauwe en Witte Muisjes",
        [
            _w("met", "preposition"), _w("De Ruijter", "proper_noun_person"),
            _w("kunnen", "verb"), _w("u", "pronoun"), _w("elk", "adjective"),
            _w("de dag", "noun"), _w("genieten", "verb"), _w("van", "preposition"),
            _w("een", "article"), _w("breed", "adjective"),
            _w("het assortiment", "noun"), _w("smakelijk", "adjective"),
            _w("het product", "noun"), _w("de chocoladevlokken", "noun"),
            _w("de melk", "noun"), _w("en", "conjunction"), _w("puur", "adjective"),
            _w("de chocoladehagel", "noun"), _w("de vruchtenhagel", "noun"),
            _w("de anijshagel", "noun"), _w("het vlokfeest", "noun"),
            _w("gestampt", "adjective"), _w("het muisje", "noun"),
            _w("roze", "adjective"), _w("wit", "adjective"), _w("blauw", "adjective"),
        ],
    ),
]
# fmt: on


def _make_ai(words: list[_W], call_id: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": TOOL_NAME, "args": {"words": words}, "id": call_id}],
    )


def _make_ack(words: list[_W], call_id: str) -> ToolMessage:
    return ToolMessage(content=json.dumps({"words": words}, ensure_ascii=False), tool_call_id=call_id)


def build_prompt() -> ChatPromptTemplate:
    """Build the Dutch word extraction prompt with few-shot examples."""
    messages: list = [SystemMessage(content=SYSTEM_INSTRUCTION)]
    for i, (text, words) in enumerate(EXAMPLES, 1):
        cid = f"call_ex_{i}"
        messages += [HumanMessage(content=text), _make_ai(words, cid), _make_ack(words, cid)]
    messages.append(MessagesPlaceholder(variable_name="text"))
    return ChatPromptTemplate.from_messages(messages)


if __name__ == "__main__":
    from nl_processing.core.scripts.prompt_author import save_prompt

    save_prompt(build_prompt(), str(OUTPUT_PATH))
