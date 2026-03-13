"""Generate prompts for miscellaneous POS: numeral, interjection, phrase.

Usage:
    uv run python src/nl_processing/extract_word_details/prompts/generate_misc_pos_prompts.py
"""

import json
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel

from nl_processing.extract_word_details.models import NlRuInterjectionDetails, NlRuNumeralDetails, NlRuPhraseDetails
from nl_processing.extract_word_details.prompts._prompt_helpers import make_example_ai


class _NumeralDetailsBatch(BaseModel):
    details: list[NlRuNumeralDetails]


class _InterjectionDetailsBatch(BaseModel):
    details: list[NlRuInterjectionDetails]


class _PhraseDetailsBatch(BaseModel):
    details: list[NlRuPhraseDetails]


def build_numeral_prompt() -> ChatPromptTemplate:
    """Build the Dutch numeral details extraction prompt."""
    system_instruction = (
        "Вы — эксперт по нидерландской грамматике. "
        "Получая нидерландское числительное, вы предоставляете подробную лингвистическую информацию: "
        "тип числительного (количественное/порядковое), форму порядкового числительного, "
        "а также обучающие материалы."
    )

    example_1 = {
        "numeral_type": "Количественное числительное",
        "ordinal_form": "eerste",
        "shared": {
            "common_phrases": [{"phrase": "een huis", "translation": "один дом"}],
            "example_sentences": [
                {"dutch_sentence": "Ik heb een boek.", "russian_explanation": "У меня есть одна книга."}
            ],
            "word_parts": [{"part": "een", "explanation_russian": "числительное 'один'"}],
            "interesting_facts": [
                {"fact_russian": "В нидерландском 'een' также является неопределённым артиклем", "dutch_parallel": None}
            ],
        },
    }

    return ChatPromptTemplate.from_messages([
        SystemMessage(content=system_instruction),
        HumanMessage(content="een"),
        make_example_ai([example_1], "call_num_1", "_NumeralDetailsBatch"),
        ToolMessage(
            content=json.dumps({"details": [example_1]}, ensure_ascii=False),
            tool_call_id="call_num_1",
        ),
        MessagesPlaceholder(variable_name="text"),
    ])


def build_interjection_prompt() -> ChatPromptTemplate:
    """Build the Dutch interjection details extraction prompt."""
    system_instruction = (
        "Вы — эксперт по нидерландской грамматике. "
        "Получая нидерландское междометие, вы предоставляете подробную лингвистическую информацию: "
        "эмоцию или контекст употребления, уровень формальности (объяснение на русском языке), "
        "а также обучающие материалы."
    )

    example_1 = {
        "emotion_or_context": "Выражает удивление или восхищение",
        "formality_level": "Неформальное, разговорное",
        "shared": {
            "common_phrases": [{"phrase": "wow, dat is mooi", "translation": "вау, это красиво"}],
            "example_sentences": [
                {"dutch_sentence": "Wow! Wat een verrassing!", "russian_explanation": "Вау! Какой сюрприз!"}
            ],
            "word_parts": [{"part": "wow", "explanation_russian": "заимствованное междометие"}],
            "interesting_facts": [{"fact_russian": "Заимствовано из английского языка", "dutch_parallel": "wauw"}],
        },
    }

    return ChatPromptTemplate.from_messages([
        SystemMessage(content=system_instruction),
        HumanMessage(content="wow"),
        make_example_ai([example_1], "call_int_1", "_InterjectionDetailsBatch"),
        ToolMessage(
            content=json.dumps({"details": [example_1]}, ensure_ascii=False),
            tool_call_id="call_int_1",
        ),
        MessagesPlaceholder(variable_name="text"),
    ])


def build_phrase_prompt() -> ChatPromptTemplate:
    """Build the Dutch phrase details extraction prompt."""
    system_instruction = (
        "Вы — эксперт по нидерландской грамматике. "
        "Получая нидерландскую фразу или выражение, вы предоставляете подробную лингвистическую информацию: "
        "дословный перевод, переносное значение, контекст употребления (объяснение на русском языке), "
        "а также обучающие материалы."
    )

    example_1 = {
        "literal_translation": "иметь масло на голове",
        "figurative_meaning": "чувствовать себя виноватым, иметь что скрывать",
        "usage_context": "Идиоматическое выражение, используемое в разговорной речи",
        "shared": {
            "common_phrases": [
                {"phrase": "Hij heeft boter op zijn hoofd", "translation": "Он чувствует себя виноватым"}
            ],
            "example_sentences": [
                {
                    "dutch_sentence": "Waarom ben je zo zenuwachtig? Heb je boter op je hoofd?",
                    "russian_explanation": "Почему ты такой нервный? Тебе есть что скрывать?",
                }
            ],
            "word_parts": [
                {"part": "boter", "explanation_russian": "масло"},
                {"part": "hoofd", "explanation_russian": "голова"},
            ],
            "interesting_facts": [
                {
                    "fact_russian": "Происходит от старинного поверья о том, что масло на голове тает от стыда",
                    "dutch_parallel": None,
                }
            ],
        },
    }

    return ChatPromptTemplate.from_messages([
        SystemMessage(content=system_instruction),
        HumanMessage(content="boter op het hoofd hebben"),
        make_example_ai([example_1], "call_phrase_1", "_PhraseDetailsBatch"),
        ToolMessage(
            content=json.dumps({"details": [example_1]}, ensure_ascii=False),
            tool_call_id="call_phrase_1",
        ),
        MessagesPlaceholder(variable_name="text"),
    ])


if __name__ == "__main__":
    from nl_processing.core.scripts.prompt_author import save_prompt

    prompts_dir = Path(__file__).parent

    save_prompt(build_numeral_prompt(), str(prompts_dir / "nl_ru_numeral.json"))
    save_prompt(build_interjection_prompt(), str(prompts_dir / "nl_ru_interjection.json"))
    save_prompt(build_phrase_prompt(), str(prompts_dir / "nl_ru_phrase.json"))
