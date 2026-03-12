"""Generate the bidirectional Dutch↔Russian translation prompt (nl_ru_bidirectional.json) with few-shot examples.

Usage:
    uv run python src/nl_processing/translate_text_bidirectional/prompts/generate_nl_ru_bidirectional_prompt.py

This script:
1. Defines the system instruction (in Russian) for bidirectional NL↔RU translation
2. Builds few-shot examples as HumanMessage + AIMessage + ToolMessage triplets
3. Serializes with dumpd() and saves to nl_ru_bidirectional.json

The script is the source of truth — nl_ru_bidirectional.json is the generated artifact.
Re-run this script whenever examples or system instruction change.
"""

from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

SYSTEM_INSTRUCTION = (
    "Вы — профессиональный двунаправленный переводчик между нидерландским и русским языками. "
    "Определите основной язык входного текста (нидерландский или русский). "
    "Если текст на нидерландском — переведите на русский, используя инструмент `_NlToRuTranslation`. "
    "Если текст на русском — переведите на нидерландский, используя инструмент `_RuToNlTranslation`. "
    "Сохраняйте всё форматирование markdown (заголовки, жирный, курсив, списки, разрывы абзацев). "
    "Верните только переведённый текст — без комментариев, пояснений и префиксов. "
    "Если ввод пуст или не содержит ни нидерландского, ни русского текста, "
    "вызовите любой инструмент с пустой строкой."
)

NL_TO_RU_TOOL = "_NlToRuTranslation"
RU_TO_NL_TOOL = "_RuToNlTranslation"

EXAMPLE_1_INPUT = "De zon schijnt vandaag."
EXAMPLE_1_OUTPUT = "Сегодня светит солнце."

EXAMPLE_2_INPUT = "Сегодня светит солнце."
EXAMPLE_2_OUTPUT = "De zon schijnt vandaag."

EXAMPLE_3_INPUT = "# Welkom\n\nDit is een **belangrijk** bericht."
EXAMPLE_3_OUTPUT = "# Добро пожаловать\n\nЭто **важное** сообщение."

EXAMPLE_4_INPUT = "# Добро пожаловать\n\nЭто **важное** сообщение."
EXAMPLE_4_OUTPUT = "# Welkom\n\nDit is een **belangrijk** bericht."

EXAMPLE_5_INPUT = "Wat heb je nodig:\n\n- *Melk*\n- *Brood*\n- *Kaas*"
EXAMPLE_5_OUTPUT = "Что тебе нужно:\n\n- *Молоко*\n- *Хлеб*\n- *Сыр*"

EXAMPLE_6_INPUT = "Что тебе нужно:\n\n- *Молоко*\n- *Хлеб*\n- *Сыр*"
EXAMPLE_6_OUTPUT = "Wat heb je nodig:\n\n- *Melk*\n- *Brood*\n- *Kaas*"

EXAMPLE_7_INPUT = ""
EXAMPLE_7_OUTPUT = ""

EXAMPLE_8_INPUT = "The quick brown fox."
EXAMPLE_8_OUTPUT = ""

OUTPUT_PATH = Path(__file__).parent / "nl_ru_bidirectional.json"


def _make_example_ai(translated_text: str, call_id: str, tool_name: str) -> AIMessage:
    """Create an AIMessage with a tool_call for the specified translation tool."""
    return AIMessage(
        content="",
        tool_calls=[{"name": tool_name, "args": {"text": translated_text}, "id": call_id}],
    )


def build_prompt() -> ChatPromptTemplate:
    """Build the bidirectional Dutch↔Russian translation prompt with 8 few-shot examples."""
    return ChatPromptTemplate.from_messages([
        SystemMessage(content=SYSTEM_INSTRUCTION),
        # Example 1: NL→RU simple sentence
        HumanMessage(content=EXAMPLE_1_INPUT),
        _make_example_ai(EXAMPLE_1_OUTPUT, "call_example_1", NL_TO_RU_TOOL),
        ToolMessage(content=EXAMPLE_1_OUTPUT, tool_call_id="call_example_1"),
        # Example 2: RU→NL simple sentence
        HumanMessage(content=EXAMPLE_2_INPUT),
        _make_example_ai(EXAMPLE_2_OUTPUT, "call_example_2", RU_TO_NL_TOOL),
        ToolMessage(content=EXAMPLE_2_OUTPUT, tool_call_id="call_example_2"),
        # Example 3: NL→RU markdown with headings and bold
        HumanMessage(content=EXAMPLE_3_INPUT),
        _make_example_ai(EXAMPLE_3_OUTPUT, "call_example_3", NL_TO_RU_TOOL),
        ToolMessage(content=EXAMPLE_3_OUTPUT, tool_call_id="call_example_3"),
        # Example 4: RU→NL markdown with headings and bold
        HumanMessage(content=EXAMPLE_4_INPUT),
        _make_example_ai(EXAMPLE_4_OUTPUT, "call_example_4", RU_TO_NL_TOOL),
        ToolMessage(content=EXAMPLE_4_OUTPUT, tool_call_id="call_example_4"),
        # Example 5: NL→RU list + italic
        HumanMessage(content=EXAMPLE_5_INPUT),
        _make_example_ai(EXAMPLE_5_OUTPUT, "call_example_5", NL_TO_RU_TOOL),
        ToolMessage(content=EXAMPLE_5_OUTPUT, tool_call_id="call_example_5"),
        # Example 6: RU→NL list + italic
        HumanMessage(content=EXAMPLE_6_INPUT),
        _make_example_ai(EXAMPLE_6_OUTPUT, "call_example_6", RU_TO_NL_TOOL),
        ToolMessage(content=EXAMPLE_6_OUTPUT, tool_call_id="call_example_6"),
        # Example 7: empty input
        HumanMessage(content=EXAMPLE_7_INPUT),
        _make_example_ai(EXAMPLE_7_OUTPUT, "call_example_7", NL_TO_RU_TOOL),
        ToolMessage(content=EXAMPLE_7_OUTPUT, tool_call_id="call_example_7"),
        # Example 8: non-NL/RU text
        HumanMessage(content=EXAMPLE_8_INPUT),
        _make_example_ai(EXAMPLE_8_OUTPUT, "call_example_8", NL_TO_RU_TOOL),
        ToolMessage(content=EXAMPLE_8_OUTPUT, tool_call_id="call_example_8"),
        # Placeholder for actual input
        MessagesPlaceholder(variable_name="text"),
    ])


if __name__ == "__main__":
    from nl_processing.core.scripts.prompt_author import save_prompt

    save_prompt(build_prompt(), str(OUTPUT_PATH))
