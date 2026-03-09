"""Generate the Dutch-image→Russian translation prompt (nl_ru.json) with few-shot examples.

Usage:
    uv run python src/nl_processing/translate_text_from_image/prompts/generate_nl_ru_prompt.py

This script:
1. Generates synthetic test images and encodes real photos
2. Builds a ChatPromptTemplate with few-shot examples combining extraction and translation
3. Serializes with dumpd() and saves to nl_ru.json

The script is the source of truth — nl_ru.json is the generated artifact.
"""

from pathlib import Path
import tempfile

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from nl_processing.core.image_encoding import encode_path_to_base64

from nl_processing.translate_text_from_image.benchmark import render_text_image

_EXAMPLES_DIR = Path(__file__).parent / "examples"
_OUTPUT_PATH = Path(__file__).parent / "nl_ru.json"
_TOOL_NAME = "_TranslatedImageText"

_SYSTEM_INSTRUCTION = (
    "Вы — профессиональный переводчик. "
    "Извлеките весь нидерландский текст из предоставленного изображения "
    "и переведите его на русский язык. "
    "Сохраняйте структуру документа как markdown "
    "(заголовки, наdruk, переносы строк). "
    "Игнорируйте текст на других языках. "
    "Если изображение не содержит нидерландского текста, верните пустую строку. "
    "Верните только перевод — без комментариев и пояснений."
)

# Example 1: Simple Dutch sentence
_EXAMPLE_1_TEXT = "De kat zit op de mat"
_EXAMPLE_1_OUTPUT = "Кот сидит на коврике"

# Example 2: Mixed Dutch/Russian - only translate Dutch
_EXAMPLE_2_TEXT = "Welkom bij ons\nДобро пожаловать"
_EXAMPLE_2_OUTPUT = "Добро пожаловать к нам"

# Example 3: Handwritten vocabulary (dutch_handwritten_mixed.jpg)
_EXAMPLE_3_OUTPUT = (
    "число\n"
    "женатый/замужняя\n"
    "не\n"
    "новый\n"
    "красивый\n"
    "высокий\n"
    "работа\n"
    "искусство\n"
    "очень\n"
    "познакомиться\n"
    "век\n"
    "усталый\n"
    "рано\n"
    "далеко\n"
    "там\n"
    "время\n"
    "читать"
)

# Example 4: Wide vocabulary (dutch_vocabulary_wide.jpg)
_EXAMPLE_4_OUTPUT = (
    "откуда\n"
    "менять\n"
    "улучшать\n"
    "рядом\n"
    "порядок\n"
    "пример\n"
    "имя\n"
    "форма\n"
    "вопрос\n"
    "подруга\n"
    "женщина\n"
    "что\n"
    "неделя\n"
    "добро пожаловать\n"
    "работать\n"
    "жить\n"
    "место жительства\n"
    "слово\n"
    "она/они\n"
    "сказать\n"
    "она\n"
    "быть\n"
    "его\n"
    "предложение"
)

# Examples 5-7: English-only images should return empty
_EXAMPLE_5_TEXT = "The quick brown fox jumps over the lazy dog"
_EXAMPLE_5_OUTPUT = ""

_EXAMPLE_6_TEXT = "Please take your shoes off before entering the house"
_EXAMPLE_6_OUTPUT = ""

_EXAMPLE_7_TEXT = "Remember to bring your umbrella tomorrow"
_EXAMPLE_7_OUTPUT = ""


def _encode_image_to_data_url(image_path: str) -> str:
    """Encode an image file to a base64 data URL."""
    b64, media_type = encode_path_to_base64(image_path)
    return f"data:{media_type};base64,{b64}"


def _render_synthetic_data_url(text: str, *, width: int = 800, height: int = 200) -> str:
    """Generate a synthetic image from text and return as data URL."""
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = render_text_image(
            text, str(Path(tmpdir) / "img.png"), image_width=width, image_height=height, scale=1.2
        )
        return _encode_image_to_data_url(img_path)


def _make_few_shot_triplet(
    image_data_url: str, expected_translation: str, call_id: str
) -> tuple[HumanMessage, AIMessage, ToolMessage]:
    """Build one few-shot example: image input → translation output → tool confirmation."""
    human = HumanMessage(content=[{"type": "image_url", "image_url": {"url": image_data_url}}])
    ai = AIMessage(
        content="",
        tool_calls=[{"name": _TOOL_NAME, "args": {"text": expected_translation}, "id": call_id}],
    )
    tool = ToolMessage(content=expected_translation, tool_call_id=call_id)
    return human, ai, tool


def build_prompt() -> ChatPromptTemplate:
    """Build the Dutch-image→Russian prompt with 7 few-shot examples."""
    # Generate synthetic images for text examples
    img1 = _render_synthetic_data_url(_EXAMPLE_1_TEXT)
    img2 = _render_synthetic_data_url(_EXAMPLE_2_TEXT)
    img5 = _render_synthetic_data_url(_EXAMPLE_5_TEXT)
    img6 = _render_synthetic_data_url(_EXAMPLE_6_TEXT)
    img7 = _render_synthetic_data_url(_EXAMPLE_7_TEXT)

    # Encode real photos
    img3 = _encode_image_to_data_url(str(_EXAMPLES_DIR / "dutch_handwritten_mixed.jpg"))
    img4 = _encode_image_to_data_url(str(_EXAMPLES_DIR / "dutch_vocabulary_wide.jpg"))

    # Build triplets for all 7 examples
    triplet1 = _make_few_shot_triplet(img1, _EXAMPLE_1_OUTPUT, "call_example_1")
    triplet2 = _make_few_shot_triplet(img2, _EXAMPLE_2_OUTPUT, "call_example_2")
    triplet3 = _make_few_shot_triplet(img3, _EXAMPLE_3_OUTPUT, "call_example_3")
    triplet4 = _make_few_shot_triplet(img4, _EXAMPLE_4_OUTPUT, "call_example_4")
    triplet5 = _make_few_shot_triplet(img5, _EXAMPLE_5_OUTPUT, "call_example_5")
    triplet6 = _make_few_shot_triplet(img6, _EXAMPLE_6_OUTPUT, "call_example_6")
    triplet7 = _make_few_shot_triplet(img7, _EXAMPLE_7_OUTPUT, "call_example_7")

    # Flatten triplets into messages
    messages = [SystemMessage(content=_SYSTEM_INSTRUCTION)]
    for triplet in [triplet1, triplet2, triplet3, triplet4, triplet5, triplet6, triplet7]:
        messages.extend(triplet)
    messages.append(MessagesPlaceholder(variable_name="images"))

    return ChatPromptTemplate.from_messages(messages)


if __name__ == "__main__":
    from nl_processing.core.scripts.prompt_author import save_prompt

    save_prompt(build_prompt(), str(_OUTPUT_PATH))
