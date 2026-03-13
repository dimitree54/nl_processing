"""Generate prompts for noun and verb POS types.

Usage:
    uv run python src/nl_processing/extract_word_details/prompts/generate_noun_verb_prompts.py
"""

import json
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel

from nl_processing.extract_word_details.models import NlRuNounDetails, NlRuVerbDetails
from nl_processing.extract_word_details.prompts._prompt_helpers import make_example_ai


class _NounDetailsBatch(BaseModel):
    details: list[NlRuNounDetails]


class _VerbDetailsBatch(BaseModel):
    details: list[NlRuVerbDetails]


def build_noun_prompt() -> ChatPromptTemplate:
    """Build the Dutch noun details extraction prompt."""
    system_instruction = (
        "Вы — эксперт по нидерландской грамматике. "
        "Получая нидерландское существительное, вы предоставляете подробную лингвистическую информацию: "
        "артикль (de/het), форму множественного числа, уменьшительную форму, объяснение рода на русском языке, "
        "а также обучающие материалы (общие фразы, примеры предложений, разбор частей слова, интересные факты)."
    )

    example_1 = {
        "article": "de",
        "plural": "huizen",
        "diminutive": "huisje",
        "gender_explanation": "Мужской род, используется артикль 'de'",
        "shared": {
            "common_phrases": [{"phrase": "thuis zijn", "translation": "быть дома"}],
            "example_sentences": [{"dutch_sentence": "Het huis is groot.", "russian_explanation": "Дом большой."}],
            "word_parts": [{"part": "huis", "explanation_russian": "корень, означающий 'жилище'"}],
            "interesting_facts": [
                {"fact_russian": "В Нидерландах исторически важна домашняя жизнь", "dutch_parallel": "gezelligheid"}
            ],
        },
    }

    return ChatPromptTemplate.from_messages([
        SystemMessage(content=system_instruction),
        HumanMessage(content="huis"),
        make_example_ai([example_1], "call_noun_1", "_NounDetailsBatch"),
        ToolMessage(
            content=json.dumps({"details": [example_1]}, ensure_ascii=False),
            tool_call_id="call_noun_1",
        ),
        MessagesPlaceholder(variable_name="text"),
    ])


def build_verb_prompt() -> ChatPromptTemplate:
    """Build the Dutch verb details extraction prompt."""
    system_instruction = (
        "Вы — эксперт по нидерландской грамматике. "
        "Получая нидерландский глагол, вы предоставляете подробную лингвистическую информацию: "
        "формы настоящего времени (ik/jij/hij/wij/zij), прошедшее время (singular/plural), "
        "причастие прошедшего времени, вспомогательный глагол (hebben/zijn), отделяемую приставку, "
        "объяснение спряжения на русском языке, а также обучающие материалы."
    )

    example_1 = {
        "present_tense": {"ik": "loop", "jij": "loopt", "hij": "loopt", "wij": "lopen", "zij": "lopen"},
        "past_simple": {"singular": "liep", "plural": "liepen"},
        "past_participle": "gelopen",
        "auxiliary": "hebben",
        "separable_prefix": None,
        "conjugation_explanation": "Сильный глагол с изменением корневой гласной в прошедшем времени",
        "shared": {
            "common_phrases": [{"phrase": "lopen naar", "translation": "идти к"}],
            "example_sentences": [{"dutch_sentence": "Ik loop naar school.", "russian_explanation": "Я иду в школу."}],
            "word_parts": [{"part": "loop", "explanation_russian": "корень, означающий 'движение пешком'"}],
            "interesting_facts": [{"fact_russian": "Голландцы очень много ходят пешком", "dutch_parallel": None}],
        },
    }

    return ChatPromptTemplate.from_messages([
        SystemMessage(content=system_instruction),
        HumanMessage(content="lopen"),
        make_example_ai([example_1], "call_verb_1", "_VerbDetailsBatch"),
        ToolMessage(
            content=json.dumps({"details": [example_1]}, ensure_ascii=False),
            tool_call_id="call_verb_1",
        ),
        MessagesPlaceholder(variable_name="text"),
    ])


if __name__ == "__main__":
    from nl_processing.core.scripts.prompt_author import save_prompt

    prompts_dir = Path(__file__).parent

    save_prompt(build_noun_prompt(), str(prompts_dir / "nl_ru_noun.json"))
    save_prompt(build_verb_prompt(), str(prompts_dir / "nl_ru_verb.json"))
