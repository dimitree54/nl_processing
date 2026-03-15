"""Generate the Dutch extraction prompt (nl.json) with few-shot examples.

Usage:
    uv run python src/nl_processing/extract_text_from_image/prompts/generate_nl_prompt.py

This script:
1. Generates synthetic test images and encodes real photos
2. Encodes them to base64
3. Builds a ChatPromptTemplate with 8 few-shot examples (HumanMessage + AIMessage + ToolMessage triplets)
4. Serializes with dumpd() and saves to nl.json

The script is the source of truth — nl.json is the generated artifact.
Re-run this script whenever example text or image parameters change.
"""

from pathlib import Path
import tempfile

from langchain_core.messages import SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from nl_processing.core.image_encoding import (
    build_image_human_message,
    encode_path_to_base64,
    generate_test_image,
)
from nl_processing.core.prompts import build_tool_call_ai_message

SYSTEM_INSTRUCTION = (
    "Je bent een tekst-extractie assistent. "
    "Extraheer alleen de Nederlandse tekst uit het aangeboden beeld. "
    "Behoud de originele documentstructuur als markdown "
    "(koppen, nadruk, regelafbrekingen). "
    "Negeer tekst in andere talen. "
    "Als er geen Nederlandse tekst zichtbaar is, retourneer dan een lege string. "
    "Beschouw Engelse tekst nooit als Nederlands en kopieer geen niet-Nederlandse tekst. "
    "Retourneer alleen de geëxtraheerde tekst, zonder commentaar of uitleg."
)

EXAMPLE_1_TEXT = "De kat zit op de mat"
EXAMPLE_1_EXPECTED = "De kat zit op de mat"

EXAMPLE_2_TEXT = "Welkom bij ons\nДобро пожаловать"
EXAMPLE_2_EXPECTED = "Welkom bij ons"

EXAMPLE_3_IMAGE = Path(__file__).parent / "examples" / "dutch_handwritten_mixed.jpg"
EXAMPLE_3_EXPECTED = (
    "getal, het\n"
    "getrouwd\n"
    "niet\n"
    "nieuw\n"
    "mooi\n"
    "hoog\n"
    "baan\n"
    "kunst\n"
    "heel\n"
    "leren kennen\n"
    "eeuw\n"
    "moe\n"
    "vroeg\n"
    "ver\n"
    "daar\n"
    "tijd\n"
    "lezen"
)

EXAMPLE_4_IMAGE = Path(__file__).parent / "examples" / "dutch_vocabulary_wide.jpg"
EXAMPLE_4_EXPECTED = (
    "vandaan\n"
    "veranderen\n"
    "verbeteren\n"
    "vlakbij\n"
    "volgorde, de\n"
    "voorbeeld, het\n"
    "voornaam, de\n"
    "vorm, de\n"
    "vraag, de\n"
    "vriendin, de\n"
    "vrouw, de\n"
    "wat\n"
    "week, de\n"
    "welkom\n"
    "werken\n"
    "wonen\n"
    "woonplaats, de\n"
    "woord, het\n"
    "ze\n"
    "zeggen\n"
    "zij\n"
    "zijn\n"
    "zijn\n"
    "zin, de"
)

EXAMPLE_5_IMAGE = Path(__file__).parent / "examples" / "dutch_vocabulary.jpg"
EXAMPLE_5_EXPECTED = (
    "vandaan\n"
    "veranderen\n"
    "verbeteren\n"
    "vlakbij\n"
    "volgorde, de\n"
    "voorbeeld, het\n"
    "voornaam, de\n"
    "vorm, de\n"
    "vraag, de\n"
    "vriendin, de\n"
    "vrouw, de\n"
    "wat\n"
    "week, de\n"
    "welkom\n"
    "werken\n"
    "wonen"
)

EXAMPLE_6_TEXT = "The quick brown fox jumps over the lazy dog"
EXAMPLE_6_EXPECTED = ""

EXAMPLE_7_TEXT = "Please take your shoes off before entering the house"
EXAMPLE_7_EXPECTED = ""

EXAMPLE_8_TEXT = "Remember to charge your phone before leaving tomorrow"
EXAMPLE_8_EXPECTED = ""

OUTPUT_PATH = Path(__file__).parent / "nl.json"


def _synthetic_human_message(text: str) -> object:
    """Generate a synthetic image with rendered text and return a HumanMessage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = str(Path(tmpdir) / "synthetic.png")
        generate_test_image(text, img_path)
        base64_string, media_type = encode_path_to_base64(img_path)
    return build_image_human_message(base64_string, media_type)


def _existing_image_human_message(path: Path) -> object:
    """Encode an existing image file and return a HumanMessage."""
    base64_string, media_type = encode_path_to_base64(str(path))
    return build_image_human_message(base64_string, media_type)


def _example(human_msg: object, expected: str, call_id: str) -> list:
    """Build one few-shot triplet: HumanMessage, AIMessage (tool call), ToolMessage."""
    return [
        human_msg,
        build_tool_call_ai_message("ExtractedText", {"text": expected}, call_id),
        ToolMessage(content=expected, tool_call_id=call_id),
    ]


def build_prompt() -> ChatPromptTemplate:
    """Build the Dutch extraction prompt with 8 few-shot examples."""
    messages = [SystemMessage(content=SYSTEM_INSTRUCTION)]
    messages += _example(_synthetic_human_message(EXAMPLE_1_TEXT), EXAMPLE_1_EXPECTED, "call_example_1")
    messages += _example(_synthetic_human_message(EXAMPLE_2_TEXT), EXAMPLE_2_EXPECTED, "call_example_2")
    messages += _example(_existing_image_human_message(EXAMPLE_3_IMAGE), EXAMPLE_3_EXPECTED, "call_example_3")
    messages += _example(_existing_image_human_message(EXAMPLE_4_IMAGE), EXAMPLE_4_EXPECTED, "call_example_4")
    messages += _example(_existing_image_human_message(EXAMPLE_5_IMAGE), EXAMPLE_5_EXPECTED, "call_example_5")
    messages += _example(_synthetic_human_message(EXAMPLE_6_TEXT), EXAMPLE_6_EXPECTED, "call_example_6")
    messages += _example(_synthetic_human_message(EXAMPLE_7_TEXT), EXAMPLE_7_EXPECTED, "call_example_7")
    messages += _example(_synthetic_human_message(EXAMPLE_8_TEXT), EXAMPLE_8_EXPECTED, "call_example_8")
    messages.append(MessagesPlaceholder(variable_name="images"))
    return ChatPromptTemplate.from_messages(messages)


if __name__ == "__main__":
    from nl_processing.core.scripts.prompt_author import save_prompt

    save_prompt(build_prompt(), str(OUTPUT_PATH))
