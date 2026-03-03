"""Generate the Dutch extraction prompt (nl.json) with few-shot examples.

Usage:
    uv run python nl_processing/extract_text_from_image/prompts/generate_nl_prompt.py

This script:
1. Generates 3 synthetic test images using benchmark.generate_test_image()
2. Encodes them to base64
3. Builds a ChatPromptTemplate with few-shot examples (HumanMessage + AIMessage + ToolMessage triplets)
4. Serializes with dumpd() and saves to nl.json

The script is the source of truth — nl.json is the generated artifact.
Re-run this script whenever example text or image parameters change.
"""

import json
from pathlib import Path
import tempfile

from langchain_core.load import dumpd
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

EXAMPLE_3_TEXT = "The quick brown fox jumps over the lazy dog"
EXAMPLE_3_EXPECTED = ""

OUTPUT_PATH = Path(__file__).parent / "nl.json"


def _generate_image_b64(text: str, *, width: int = 800, height: int = 200) -> str:
    """Generate a synthetic image and return its base64 data URL."""
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = str(Path(tmpdir) / "image.png")
        generate_test_image(text, img_path, width=width, height=height, font_scale=1.2)
        b64, media_type = encode_path_to_base64(img_path)
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
    """Build the Dutch extraction prompt with 3 few-shot examples."""
    img1 = _generate_image_b64(EXAMPLE_1_TEXT)
    img2 = _generate_image_b64(EXAMPLE_2_TEXT)
    img3 = _generate_image_b64(EXAMPLE_3_TEXT)

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
        MessagesPlaceholder(variable_name="images"),
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
