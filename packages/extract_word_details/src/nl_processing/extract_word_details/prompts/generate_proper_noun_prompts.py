"""Generate prompts for proper noun POS types.

Usage:
    uv run python src/nl_processing/extract_word_details/prompts/generate_proper_noun_prompts.py
"""

import json
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel

from nl_processing.extract_word_details.models import NlRuProperNounCountryDetails, NlRuProperNounPersonDetails


class _ProperNounPersonDetailsBatch(BaseModel):
    details: list[NlRuProperNounPersonDetails]


class _ProperNounCountryDetailsBatch(BaseModel):
    details: list[NlRuProperNounCountryDetails]


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


def build_proper_noun_person_prompt() -> ChatPromptTemplate:
    """Build the Dutch proper noun (person) details extraction prompt."""
    system_instruction = (
        "Вы — эксперт по нидерландской грамматике. "
        "Получая нидерландское имя собственное (имя человека), вы предоставляете подробную лингвистическую информацию: "
        "происхождение имени, культурный контекст (объяснение на русском языке), "
        "а также обучающие материалы."
    )

    example_1 = {
        "origin_explanation": "Традиционное нидерландское имя германского происхождения",
        "cultural_context": "Популярное мужское имя в Нидерландах, особенно в XX веке",
        "shared": {
            "common_phrases": [{"phrase": "Jan en alleman", "translation": "Иван да Марья (любой человек)"}],
            "example_sentences": [{"dutch_sentence": "Jan is mijn vriend.", "russian_explanation": "Ян мой друг."}],
            "word_parts": [{"part": "Jan", "explanation_russian": "сокращённая форма имени Johannes"}],
            "interesting_facts": [
                {"fact_russian": "Одно из самых популярных имён в нидерландской истории", "dutch_parallel": None}
            ],
        },
    }

    return ChatPromptTemplate.from_messages([
        SystemMessage(content=system_instruction),
        HumanMessage(content="Jan"),
        _make_example_ai([example_1], "call_person_1", "_ProperNounPersonDetailsBatch"),
        ToolMessage(
            content=json.dumps({"details": [example_1]}, ensure_ascii=False),
            tool_call_id="call_person_1",
        ),
        MessagesPlaceholder(variable_name="text"),
    ])


def build_proper_noun_country_prompt() -> ChatPromptTemplate:
    """Build the Dutch proper noun (country) details extraction prompt."""
    system_instruction = (
        "Вы — эксперт по нидерландской грамматике. "
        "Получая нидерландское название страны, вы предоставляете подробную лингвистическую информацию: "
        "нидерландское название, русское название, прилагательное национальности (на нидерландском), "
        "существительное национальности (на нидерландском), культурный контекст (объяснение на русском языке), "
        "а также обучающие материалы."
    )

    example_1 = {
        "dutch_name": "Nederland",
        "russian_name": "Нидерланды",
        "nationality_adjective": "Nederlands",
        "nationality_noun": "Nederlander",
        "cultural_context": "Официальное название королевства, включающего европейскую часть и заморские территории",
        "shared": {
            "common_phrases": [{"phrase": "uit Nederland", "translation": "из Нидерландов"}],
            "example_sentences": [
                {"dutch_sentence": "Ik kom uit Nederland.", "russian_explanation": "Я из Нидерландов."}
            ],
            "word_parts": [
                {"part": "Neder-", "explanation_russian": "нижний"},
                {"part": "-land", "explanation_russian": "земля"},
            ],
            "interesting_facts": [
                {
                    "fact_russian": "Название означает 'нижние земли', что отражает низкое расположение страны",
                    "dutch_parallel": None,
                }
            ],
        },
    }

    return ChatPromptTemplate.from_messages([
        SystemMessage(content=system_instruction),
        HumanMessage(content="Nederland"),
        _make_example_ai([example_1], "call_country_1", "_ProperNounCountryDetailsBatch"),
        ToolMessage(
            content=json.dumps({"details": [example_1]}, ensure_ascii=False),
            tool_call_id="call_country_1",
        ),
        MessagesPlaceholder(variable_name="text"),
    ])


if __name__ == "__main__":
    from nl_processing.core.scripts.prompt_author import save_prompt

    prompts_dir = Path(__file__).parent

    save_prompt(build_proper_noun_person_prompt(), str(prompts_dir / "nl_ru_proper_noun_person.json"))
    save_prompt(build_proper_noun_country_prompt(), str(prompts_dir / "nl_ru_proper_noun_country.json"))
