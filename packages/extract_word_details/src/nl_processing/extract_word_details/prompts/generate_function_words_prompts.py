"""Generate prompts for functional words: preposition, conjunction, pronoun, article.

Usage:
    uv run python src/nl_processing/extract_word_details/prompts/generate_function_words_prompts.py
"""

import json
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel

from nl_processing.extract_word_details.models import (
    NlRuArticleDetails,
    NlRuConjunctionDetails,
    NlRuPrepositionDetails,
    NlRuPronounDetails,
)


class _PrepositionDetailsBatch(BaseModel):
    details: list[NlRuPrepositionDetails]


class _ConjunctionDetailsBatch(BaseModel):
    details: list[NlRuConjunctionDetails]


class _PronounDetailsBatch(BaseModel):
    details: list[NlRuPronounDetails]


class _ArticleDetailsBatch(BaseModel):
    details: list[NlRuArticleDetails]


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


def build_preposition_prompt() -> ChatPromptTemplate:
    """Build the Dutch preposition details extraction prompt."""
    system_instruction = (
        "Вы — эксперт по нидерландской грамматике. "
        "Получая нидерландский предлог, вы предоставляете подробную лингвистическую информацию: "
        "падежное управление, пространственное или временное значение (объяснение на русском языке), "
        "а также обучающие материалы."
    )

    example_1 = {
        "case_governance": "Управляет дательным падежом, указывает на направление движения",
        "spatial_or_temporal": "Пространственный предлог, обозначает движение к цели",
        "shared": {
            "common_phrases": [{"phrase": "naar huis", "translation": "домой"}],
            "example_sentences": [{"dutch_sentence": "Ik ga naar school.", "russian_explanation": "Я иду в школу."}],
            "word_parts": [{"part": "naar", "explanation_russian": "предлог направления"}],
            "interesting_facts": [
                {"fact_russian": "Один из самых частых предлогов движения в нидерландском", "dutch_parallel": None}
            ],
        },
    }

    return ChatPromptTemplate.from_messages([
        SystemMessage(content=system_instruction),
        HumanMessage(content="naar"),
        _make_example_ai([example_1], "call_prep_1", "_PrepositionDetailsBatch"),
        ToolMessage(
            content=json.dumps({"details": [example_1]}, ensure_ascii=False),
            tool_call_id="call_prep_1",
        ),
        MessagesPlaceholder(variable_name="text"),
    ])


def build_conjunction_prompt() -> ChatPromptTemplate:
    """Build the Dutch conjunction details extraction prompt."""
    system_instruction = (
        "Вы — эксперт по нидерландской грамматике. "
        "Получая нидерландский союз, вы предоставляете подробную лингвистическую информацию: "
        "тип союза (сочинительный/подчинительный), влияние на порядок слов (объяснение на русском языке), "
        "а также обучающие материалы."
    )

    example_1 = {
        "conjunction_type": "Сочинительный союз, соединяет равноправные части",
        "word_order_effect": "Не влияет на порядок слов, сохраняется прямой порядок",
        "shared": {
            "common_phrases": [{"phrase": "en dan", "translation": "и тогда"}],
            "example_sentences": [{"dutch_sentence": "Ik eet en ik drink.", "russian_explanation": "Я ем и пью."}],
            "word_parts": [{"part": "en", "explanation_russian": "простой соединительный союз"}],
            "interesting_facts": [
                {"fact_russian": "Самый употребительный союз в нидерландском языке", "dutch_parallel": None}
            ],
        },
    }

    return ChatPromptTemplate.from_messages([
        SystemMessage(content=system_instruction),
        HumanMessage(content="en"),
        _make_example_ai([example_1], "call_conj_1", "_ConjunctionDetailsBatch"),
        ToolMessage(
            content=json.dumps({"details": [example_1]}, ensure_ascii=False),
            tool_call_id="call_conj_1",
        ),
        MessagesPlaceholder(variable_name="text"),
    ])


def build_pronoun_prompt() -> ChatPromptTemplate:
    """Build the Dutch pronoun details extraction prompt."""
    system_instruction = (
        "Вы — эксперт по нидерландской грамматике. "
        "Получая нидерландское местоимение, вы предоставляете подробную лингвистическую информацию: "
        "тип местоимения, формы склонения, объяснение на русском языке, "
        "а также обучающие материалы."
    )

    example_1 = {
        "pronoun_type": "Личное местоимение первого лица единственного числа",
        "declension_forms": ["ik", "mij", "me"],
        "shared": {
            "common_phrases": [{"phrase": "ik ben", "translation": "я есть"}],
            "example_sentences": [{"dutch_sentence": "Ik ben student.", "russian_explanation": "Я студент."}],
            "word_parts": [{"part": "ik", "explanation_russian": "личное местоимение"}],
            "interesting_facts": [
                {"fact_russian": "В нидерландском 'ik' всегда пишется с маленькой буквы", "dutch_parallel": None}
            ],
        },
    }

    return ChatPromptTemplate.from_messages([
        SystemMessage(content=system_instruction),
        HumanMessage(content="ik"),
        _make_example_ai([example_1], "call_pron_1", "_PronounDetailsBatch"),
        ToolMessage(
            content=json.dumps({"details": [example_1]}, ensure_ascii=False),
            tool_call_id="call_pron_1",
        ),
        MessagesPlaceholder(variable_name="text"),
    ])


def build_article_prompt() -> ChatPromptTemplate:
    """Build the Dutch article details extraction prompt."""
    system_instruction = (
        "Вы — эксперт по нидерландской грамматике. "
        "Получая нидерландский артикль, вы предоставляете подробную лингвистическую информацию: "
        "тип артикля (определённый/неопределённый), правила рода, объяснение на русском языке, "
        "а также обучающие материалы."
    )

    example_1 = {
        "article_type": "Определённый артикль мужского и женского рода",
        "gender_rules": "Используется с мужского и женского рода существительными, но не со средним родом",
        "shared": {
            "common_phrases": [{"phrase": "de man", "translation": "мужчина"}],
            "example_sentences": [{"dutch_sentence": "De hond is groot.", "russian_explanation": "Собака большая."}],
            "word_parts": [{"part": "de", "explanation_russian": "определённый артикль"}],
            "interesting_facts": [
                {
                    "fact_russian": "В отличие от немецкого, в нидерландском только два артикля: de и het",
                    "dutch_parallel": None,
                }
            ],
        },
    }

    return ChatPromptTemplate.from_messages([
        SystemMessage(content=system_instruction),
        HumanMessage(content="de"),
        _make_example_ai([example_1], "call_art_1", "_ArticleDetailsBatch"),
        ToolMessage(
            content=json.dumps({"details": [example_1]}, ensure_ascii=False),
            tool_call_id="call_art_1",
        ),
        MessagesPlaceholder(variable_name="text"),
    ])


if __name__ == "__main__":
    from nl_processing.core.scripts.prompt_author import save_prompt

    prompts_dir = Path(__file__).parent

    save_prompt(build_preposition_prompt(), str(prompts_dir / "nl_ru_preposition.json"))
    save_prompt(build_conjunction_prompt(), str(prompts_dir / "nl_ru_conjunction.json"))
    save_prompt(build_pronoun_prompt(), str(prompts_dir / "nl_ru_pronoun.json"))
    save_prompt(build_article_prompt(), str(prompts_dir / "nl_ru_article.json"))
