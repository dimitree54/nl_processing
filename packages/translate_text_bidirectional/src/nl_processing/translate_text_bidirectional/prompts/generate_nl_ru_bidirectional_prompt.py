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
from nl_processing.core.models import Language

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

EXAMPLE_7_INPUT = ""
EXAMPLE_7_OUTPUT = ""

# Example 8: non-source language input goes to source language
# For source=NL,target=RU: English input -> Dutch output (using RU->NL tool)
EXAMPLE_8_INPUT = "The quick brown fox."
EXAMPLE_8_OUTPUT = "De snelle bruine vos."

OUTPUT_PATH = Path(__file__).parent / "nl_ru_bidirectional.json"


def _make_example_ai(translated_text: str, call_id: str, tool_name: str) -> AIMessage:
    """Create an AIMessage with a tool_call for the specified translation tool."""
    return AIMessage(
        content="",
        tool_calls=[{"name": tool_name, "args": {"text": translated_text}, "id": call_id}],
    )


def build_dynamic_prompt(*, source_language: Language, target_language: Language) -> ChatPromptTemplate:
    """Build a bidirectional prompt with source-anchored semantics based on configured languages."""
    # Generate dynamic system instruction
    if source_language == Language.NL and target_language == Language.RU:
        source_name, target_name = "нидерландский", "русский"
        source_tool, target_tool = (
            RU_TO_NL_TOOL,
            NL_TO_RU_TOOL,
        )  # source->target uses NL->RU, non-source->source uses RU->NL
    elif source_language == Language.RU and target_language == Language.NL:
        source_name, target_name = "русский", "нидерландский"
        source_tool, target_tool = (
            NL_TO_RU_TOOL,
            RU_TO_NL_TOOL,
        )  # source->target uses RU->NL, non-source->source uses NL->RU
    else:
        msg = f"Unsupported configuration: source={source_language}, target={target_language}"
        raise ValueError(msg)

    dynamic_instruction = (
        f"Вы — профессиональный двунаправленный переводчик между нидерландским и русским языками "
        f"с поддержкой конфигурируемой семантики на основе исходного языка. "
        f"Переводите согласно следующему правилу: "
        f"если входной текст на {source_name} языке (сконфигурированный исходный язык), "
        f"переведите на {target_name} язык, используя инструмент `{target_tool}`. "
        f"Если входной текст НЕ на {source_name} языке (включая {target_name}, английский, и т.д.), "
        f"переведите на {source_name} язык, используя инструмент `{source_tool}`. "
        f"Сохраняйте всё форматирование markdown (заголовки, жирный, курсив, списки, разрывы абзацев). "
        f"Верните только переведённый текст — без комментариев, пояснений и префиксов. "
        f"Для пустого ввода используйте любой инструмент с пустой строкой."
    )

    messages = [
        SystemMessage(content=dynamic_instruction),
        # Example 1: Source language to target language
        HumanMessage(content=EXAMPLE_1_INPUT if source_language == Language.NL else EXAMPLE_2_INPUT),
        _make_example_ai(
            EXAMPLE_1_OUTPUT if source_language == Language.NL else EXAMPLE_2_OUTPUT, "call_example_1", target_tool
        ),
        ToolMessage(
            content=EXAMPLE_1_OUTPUT if source_language == Language.NL else EXAMPLE_2_OUTPUT,
            tool_call_id="call_example_1",
        ),
        # Example 2: Target language (non-source) to source language
        HumanMessage(content=EXAMPLE_2_INPUT if source_language == Language.NL else EXAMPLE_1_INPUT),
        _make_example_ai(
            EXAMPLE_2_OUTPUT if source_language == Language.NL else EXAMPLE_1_OUTPUT, "call_example_2", source_tool
        ),
        ToolMessage(
            content=EXAMPLE_2_OUTPUT if source_language == Language.NL else EXAMPLE_1_OUTPUT,
            tool_call_id="call_example_2",
        ),
        # Example 3: Source markdown to target
        HumanMessage(content=EXAMPLE_3_INPUT if source_language == Language.NL else EXAMPLE_4_INPUT),
        _make_example_ai(
            EXAMPLE_3_OUTPUT if source_language == Language.NL else EXAMPLE_4_OUTPUT, "call_example_3", target_tool
        ),
        ToolMessage(
            content=EXAMPLE_3_OUTPUT if source_language == Language.NL else EXAMPLE_4_OUTPUT,
            tool_call_id="call_example_3",
        ),
        # Example 4: Target markdown (non-source) to source
        HumanMessage(content=EXAMPLE_4_INPUT if source_language == Language.NL else EXAMPLE_3_INPUT),
        _make_example_ai(
            EXAMPLE_4_OUTPUT if source_language == Language.NL else EXAMPLE_3_OUTPUT, "call_example_4", source_tool
        ),
        ToolMessage(
            content=EXAMPLE_4_OUTPUT if source_language == Language.NL else EXAMPLE_3_OUTPUT,
            tool_call_id="call_example_4",
        ),
        # Example 5: Empty input
        HumanMessage(content=EXAMPLE_7_INPUT),
        _make_example_ai(EXAMPLE_7_OUTPUT, "call_example_5", target_tool),
        ToolMessage(content=EXAMPLE_7_OUTPUT, tool_call_id="call_example_5"),
        # Example 6: Non-source, non-target language (English) -> source language
        HumanMessage(content=EXAMPLE_8_INPUT),
        _make_example_ai(
            EXAMPLE_8_OUTPUT if source_language == Language.NL else "Быстрая коричневая лиса.",
            "call_example_6",
            source_tool,
        ),
        ToolMessage(
            content=EXAMPLE_8_OUTPUT if source_language == Language.NL else "Быстрая коричневая лиса.",
            tool_call_id="call_example_6",
        ),
        # Placeholder for actual input
        MessagesPlaceholder(variable_name="text"),
    ]

    return ChatPromptTemplate.from_messages(messages)


def build_prompt() -> ChatPromptTemplate:
    """Build the bidirectional Dutch↔Russian translation prompt with source-anchored semantics and 9 examples.

    NOTE: This static version assumes source=NL,target=RU configuration and is used only for generating
    the static JSON artifact. Runtime behavior uses build_dynamic_prompt() with actual constructor parameters.
    """
    return build_dynamic_prompt(source_language=Language.NL, target_language=Language.RU)


if __name__ == "__main__":
    from nl_processing.core.scripts.prompt_author import save_prompt

    save_prompt(build_prompt(), str(OUTPUT_PATH))
