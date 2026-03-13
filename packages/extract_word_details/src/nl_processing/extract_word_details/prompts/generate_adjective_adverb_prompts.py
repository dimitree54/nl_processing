"""Generate prompts for adjective and adverb POS types.

Usage:
    uv run python src/nl_processing/extract_word_details/prompts/generate_adjective_adverb_prompts.py
"""

import json
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel

from nl_processing.extract_word_details.models import NlRuAdjectiveDetails, NlRuAdverbDetails


class _AdjectiveDetailsBatch(BaseModel):
    details: list[NlRuAdjectiveDetails]


class _AdverbDetailsBatch(BaseModel):
    details: list[NlRuAdverbDetails]


def _make_example_ai(details: list[dict], call_id: str, batch_name: str) -> AIMessage:
    """Create an AIMessage with a tool_call for the batch model."""
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": batch_name,
                "args": {"details": details},
                "id": call_id,
            }
        ],
    )


def build_adjective_prompt() -> ChatPromptTemplate:
    """Build the Dutch adjective details extraction prompt."""
    system_instruction = (
        "Вы — эксперт по нидерландской грамматике. "
        "Получая нидерландское прилагательное, вы предоставляете подробную лингвистическую информацию: "
        "сравнительную степень, превосходную степень, флексированную форму (с -e), "
        "объяснение употребления на русском языке, а также обучающие материалы."
    )

    example_1 = {
        "comparative": "groter",
        "superlative": "grootst",
        "inflected_form": "grote",
        "usage_explanation": "Используется флексированная форма 'grote' перед определённым существительным",
        "shared": {
            "common_phrases": [{"phrase": "groot huis", "translation": "большой дом"}],
            "example_sentences": [{"dutch_sentence": "Een grote hond.", "russian_explanation": "Большая собака."}],
            "word_parts": [{"part": "groot", "explanation_russian": "корень, означающий 'размер'"}],
            "interesting_facts": [
                {"fact_russian": "Флексия прилагательных — важная черта нидерландского", "dutch_parallel": None}
            ],
        },
    }

    return ChatPromptTemplate.from_messages([
        SystemMessage(content=system_instruction),
        HumanMessage(content="groot"),
        _make_example_ai([example_1], "call_adj_1", "_AdjectiveDetailsBatch"),
        ToolMessage(
            content=json.dumps({"details": [example_1]}, ensure_ascii=False),
            tool_call_id="call_adj_1",
        ),
        MessagesPlaceholder(variable_name="text"),
    ])


def build_adverb_prompt() -> ChatPromptTemplate:
    """Build the Dutch adverb details extraction prompt."""
    system_instruction = (
        "Вы — эксперт по нидерландской грамматике. "
        "Получая нидерландское наречие, вы предоставляете подробную лингвистическую информацию: "
        "контекст употребления, позицию в предложении (объяснение на русском языке), "
        "а также обучающие материалы."
    )

    example_1 = {
        "usage_context": "Наречие времени, указывающее на скорость действия",
        "position_in_sentence": "Обычно ставится после глагола или в конце предложения",
        "shared": {
            "common_phrases": [{"phrase": "snel lopen", "translation": "быстро идти"}],
            "example_sentences": [{"dutch_sentence": "Hij loopt snel.", "russian_explanation": "Он идёт быстро."}],
            "word_parts": [{"part": "snel", "explanation_russian": "корень, означающий 'скорость'"}],
            "interesting_facts": [{"fact_russian": "Голландцы ценят эффективность и скорость", "dutch_parallel": None}],
        },
    }

    return ChatPromptTemplate.from_messages([
        SystemMessage(content=system_instruction),
        HumanMessage(content="snel"),
        _make_example_ai([example_1], "call_adv_1", "_AdverbDetailsBatch"),
        ToolMessage(
            content=json.dumps({"details": [example_1]}, ensure_ascii=False),
            tool_call_id="call_adv_1",
        ),
        MessagesPlaceholder(variable_name="text"),
    ])


if __name__ == "__main__":
    from nl_processing.core.scripts.prompt_author import save_prompt

    prompts_dir = Path(__file__).parent

    save_prompt(build_adjective_prompt(), str(prompts_dir / "nl_ru_adjective.json"))
    save_prompt(build_adverb_prompt(), str(prompts_dir / "nl_ru_adverb.json"))
