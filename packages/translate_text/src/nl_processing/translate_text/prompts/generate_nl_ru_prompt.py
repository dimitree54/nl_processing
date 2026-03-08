"""Generate the Dutch→Russian translation prompt (nl_ru.json) with few-shot examples.

Usage:
    uv run python src/nl_processing/translate_text/prompts/generate_nl_ru_prompt.py

This script:
1. Defines the system instruction (in Russian) for a professional NL→RU translator
2. Builds few-shot examples as HumanMessage + AIMessage + ToolMessage triplets
3. Serializes with dumpd() and saves to nl_ru.json

The script is the source of truth — nl_ru.json is the generated artifact.
Re-run this script whenever examples or system instruction change.
"""

from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

SYSTEM_INSTRUCTION = (
    "Вы — профессиональный переводчик с нидерландского на русский язык. "
    "Переведите предоставленный текст естественно, сохраняя смысл близко к оригиналу. "
    "Сохраняйте всё форматирование markdown (заголовки, жирный, курсив, списки, разрывы абзацев). "
    "Верните только переведённый текст — без комментариев, пояснений и префиксов. "
    "Если ввод пуст или не содержит нидерландского текста, верните пустую строку."
)

TOOL_NAME = "_TranslatedText"

EXAMPLE_1_INPUT = "De zon schijnt vandaag."
EXAMPLE_1_OUTPUT = "Сегодня светит солнце."

EXAMPLE_2_INPUT = "# Welkom\n\nDit is een **belangrijk** bericht."
EXAMPLE_2_OUTPUT = "# Добро пожаловать\n\nЭто **важное** сообщение."

EXAMPLE_3_INPUT = "Wat heb je nodig:\n\n- *Melk*\n- *Brood*\n- *Kaas*"
EXAMPLE_3_OUTPUT = "Что тебе нужно:\n\n- *Молоко*\n- *Хлеб*\n- *Сыр*"

EXAMPLE_4_INPUT = ""
EXAMPLE_4_OUTPUT = ""

EXAMPLE_5_INPUT = "The quick brown fox jumps over the lazy dog."
EXAMPLE_5_OUTPUT = ""

OUTPUT_PATH = Path(__file__).parent / "nl_ru.json"


def _make_example_ai(translated_text: str, call_id: str) -> AIMessage:
    """Create an AIMessage with a tool_call for _TranslatedText."""
    return AIMessage(
        content="",
        tool_calls=[{"name": TOOL_NAME, "args": {"text": translated_text}, "id": call_id}],
    )


def build_prompt() -> ChatPromptTemplate:
    """Build the Dutch→Russian translation prompt with 5 few-shot examples."""
    return ChatPromptTemplate.from_messages([
        SystemMessage(content=SYSTEM_INSTRUCTION),
        # Example 1: simple sentence
        HumanMessage(content=EXAMPLE_1_INPUT),
        _make_example_ai(EXAMPLE_1_OUTPUT, "call_example_1"),
        ToolMessage(content=EXAMPLE_1_OUTPUT, tool_call_id="call_example_1"),
        # Example 2: markdown with headings and bold
        HumanMessage(content=EXAMPLE_2_INPUT),
        _make_example_ai(EXAMPLE_2_OUTPUT, "call_example_2"),
        ToolMessage(content=EXAMPLE_2_OUTPUT, tool_call_id="call_example_2"),
        # Example 3: list + italic
        HumanMessage(content=EXAMPLE_3_INPUT),
        _make_example_ai(EXAMPLE_3_OUTPUT, "call_example_3"),
        ToolMessage(content=EXAMPLE_3_OUTPUT, tool_call_id="call_example_3"),
        # Example 4: empty input
        HumanMessage(content=EXAMPLE_4_INPUT),
        _make_example_ai(EXAMPLE_4_OUTPUT, "call_example_4"),
        ToolMessage(content=EXAMPLE_4_OUTPUT, tool_call_id="call_example_4"),
        # Example 5: non-Dutch text
        HumanMessage(content=EXAMPLE_5_INPUT),
        _make_example_ai(EXAMPLE_5_OUTPUT, "call_example_5"),
        ToolMessage(content=EXAMPLE_5_OUTPUT, tool_call_id="call_example_5"),
        # Placeholder for actual input
        MessagesPlaceholder(variable_name="text"),
    ])


if __name__ == "__main__":
    from nl_processing.core.scripts.prompt_author import save_prompt

    save_prompt(build_prompt(), str(OUTPUT_PATH))
