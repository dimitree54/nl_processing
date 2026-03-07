"""Generate the Dutch extraction prompt (nl.json) with few-shot examples.

Usage:
    uv run python nl_processing/extract_text_from_image/prompts/generate_nl_prompt.py

This script:
1. Generates synthetic test images and encodes real photos
2. Encodes them to base64
3. Builds a ChatPromptTemplate with 7 few-shot examples (HumanMessage + AIMessage + ToolMessage triplets)
4. Serializes with dumpd() and saves to nl.json

The script is the source of truth — nl.json is the generated artifact.
Re-run this script whenever example text or image parameters change.
"""

from pathlib import Path
import tempfile

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from nl_processing.extract_text_from_image.benchmark import generate_test_image
from nl_processing.extract_text_from_image.image_encoding import encode_path_to_base64

SYSTEM_INSTRUCTION = (
    "Je bent een tekst-extractie assistent. "
    "Extraheer alleen de Nederlandse tekst uit het aangeboden beeld. "
    "Behoud de originele documentstructuur als markdown "
    "(koppen, nadruk, regelafbrekingen). "
    "Negeer tekst in andere talen. "
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

EXAMPLE_5_TEXT = "The quick brown fox jumps over the lazy dog"
EXAMPLE_5_EXPECTED = ""

EXAMPLE_6_TEXT = "Please take your shoes off before entering the house"
EXAMPLE_6_EXPECTED = ""

EXAMPLE_7_TEXT = "Remember to bring your umbrella tomorrow"
EXAMPLE_7_EXPECTED = ""

OUTPUT_PATH = Path(__file__).parent / "nl.json"


def _generate_image_b64(text: str, *, width: int = 800, height: int = 200) -> str:
    """Generate a synthetic image and return its base64 data URL."""
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = str(Path(tmpdir) / "image.png")
        generate_test_image(text, img_path, width=width, height=height, font_scale=1.2)
        b64, media_type = encode_path_to_base64(img_path)
    return f"data:{media_type};base64,{b64}"


def _encode_existing_image_b64(path: Path) -> str:
    """Encode an existing image file and return its base64 data URL."""
    b64, media_type = encode_path_to_base64(str(path))
    return f"data:{media_type};base64,{b64}"


def _make_example_human(image_data_url: str) -> HumanMessage:
    """Create a HumanMessage with an image content block."""
    return HumanMessage(
        content=[
            {"type": "image_url", "image_url": {"url": image_data_url}},
        ]
    )


def _make_example_ai(expected_text: str, call_id: str) -> AIMessage:
    """Create an AIMessage with a tool_call for ExtractedText."""
    return AIMessage(
        content="",
        tool_calls=[{"name": "ExtractedText", "args": {"text": expected_text}, "id": call_id}],
    )


def build_prompt() -> ChatPromptTemplate:
    """Build the Dutch extraction prompt with 7 few-shot examples."""
    img1 = _generate_image_b64(EXAMPLE_1_TEXT)
    img2 = _generate_image_b64(EXAMPLE_2_TEXT)
    img3 = _encode_existing_image_b64(EXAMPLE_3_IMAGE)
    img4 = _encode_existing_image_b64(EXAMPLE_4_IMAGE)
    img5 = _generate_image_b64(EXAMPLE_5_TEXT)
    img6 = _generate_image_b64(EXAMPLE_6_TEXT)
    img7 = _generate_image_b64(EXAMPLE_7_TEXT)

    return ChatPromptTemplate.from_messages([
        SystemMessage(content=SYSTEM_INSTRUCTION),
        _make_example_human(img1),
        _make_example_ai(EXAMPLE_1_EXPECTED, "call_example_1"),
        ToolMessage(content=EXAMPLE_1_EXPECTED, tool_call_id="call_example_1"),
        _make_example_human(img2),
        _make_example_ai(EXAMPLE_2_EXPECTED, "call_example_2"),
        ToolMessage(content=EXAMPLE_2_EXPECTED, tool_call_id="call_example_2"),
        _make_example_human(img3),
        _make_example_ai(EXAMPLE_3_EXPECTED, "call_example_3"),
        ToolMessage(content=EXAMPLE_3_EXPECTED, tool_call_id="call_example_3"),
        _make_example_human(img4),
        _make_example_ai(EXAMPLE_4_EXPECTED, "call_example_4"),
        ToolMessage(content=EXAMPLE_4_EXPECTED, tool_call_id="call_example_4"),
        _make_example_human(img5),
        _make_example_ai(EXAMPLE_5_EXPECTED, "call_example_5"),
        ToolMessage(content=EXAMPLE_5_EXPECTED, tool_call_id="call_example_5"),
        _make_example_human(img6),
        _make_example_ai(EXAMPLE_6_EXPECTED, "call_example_6"),
        ToolMessage(content=EXAMPLE_6_EXPECTED, tool_call_id="call_example_6"),
        _make_example_human(img7),
        _make_example_ai(EXAMPLE_7_EXPECTED, "call_example_7"),
        ToolMessage(content=EXAMPLE_7_EXPECTED, tool_call_id="call_example_7"),
        MessagesPlaceholder(variable_name="images"),
    ])


if __name__ == "__main__":
    from nl_processing.core.scripts.prompt_author import save_prompt

    save_prompt(build_prompt(), str(OUTPUT_PATH))
