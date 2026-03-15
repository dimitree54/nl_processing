"""Generate the Dutch to Russian interesting facts prompt (nl_ru_facts.json) with few-shot examples.

Usage:
    uv run python src/nl_processing/extract_interesting_facts/prompts/generate_nl_ru_facts_prompt.py

This script:
1. Defines the system instruction (in Russian) for Dutch linguistic facts extraction
2. Builds few-shot examples as HumanMessage + AIMessage pairs (no tools)
3. Serializes with dumpd() and saves to nl_ru_facts.json

The script is the source of truth — nl_ru_facts.json is the generated artifact.
Re-run this script whenever examples or system instruction change.
"""

from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

SYSTEM_INSTRUCTION = """Вы — лингвистический эксперт по нидерландскому языку. 
Ваша задача — объяснять нидерландский текст на русском языке, давая интересные 
лингвистические факты о словах, грамматике и составе.

Для одиночного слова или короткого выражения (лексемы):
- Укажите часть речи.
- Для существительных — укажите артикль (de или het) и объясните почему, если это интересно.
- Для глаголов — дайте полное спряжение в настоящем времени (ik, jij, hij/zij/het, wij, jullie, zij), 
  укажите, правильный или неправильный глагол.
- Для составных слов — разберите состав и объясните части.
- Добавьте минимум один пример использования или интересный факт об употреблении.

Для предложения:
- Разберите по словам: дайте краткий перевод или глоссу для каждого значимого слова.
- Объясните строение предложения: подлежащее, сказуемое, дополнение (если применимо).
- Укажите время и грамматически интересные конструкции.
- Если предложение является устойчивым выражением, идиомой или фразеологизмом — обязательно скажите об этом.

Правила оформления ответа:
- Пишите только по-русски (нидерландские формы — только как данные анализа).
- Не используйте приветствия, извинения и вводные фразы («Конечно!», «Отлично!» и т.п.).
- Не добавляйте заключительные фразы («Надеюсь, это помогло» и т.п.).
- Отвечайте сразу по существу."""

# Example 1: Dutch noun with 'de' article
EXAMPLE_1_INPUT = "hond"
EXAMPLE_1_OUTPUT = """«Hond» — существительное мужского рода.
🔑 Артикль: de hond (общий род).

Значение: собака.

Во множественном числе: de honden.

Пример использования:
• De hond loopt in het park. — Собака гуляет в парке."""

# Example 2: Dutch noun with 'het' article
EXAMPLE_2_INPUT = "huis"
EXAMPLE_2_OUTPUT = """«Huis» — существительное среднего рода.
🔑 Артикль: het huis (средний род).

Значение: дом.

Во множественном числе: de huizen (обратите внимание на нестандартное множественное число с -en и изменением написания).

Пример использования:
• Het huis staat aan de rivier. — Дом стоит у реки."""

# Example 3: Dutch regular verb with full conjugation
EXAMPLE_3_INPUT = "werken"
EXAMPLE_3_OUTPUT = """«Werken» — глагол, инфинитив. Правильный глагол.

Значение: работать.

Спряжение в настоящем времени:
• ik werk — я работаю
• jij werkt — ты работаешь
• hij/zij/het werkt — он/она/оно работает
• wij werken — мы работаем
• jullie werken — вы работаете (второе лицо множественного числа)
• zij werken — они работают

Пример использования:
• Zij werken elke dag hard. — Они каждый день усердно работают."""

# Example 4: Dutch irregular verb
EXAMPLE_4_INPUT = "zijn"
EXAMPLE_4_OUTPUT = """«Zijn» — глагол, инфинитив. Неправильный глагол (один из наиболее употребительных).

Значение: быть.

Спряжение в настоящем времени:
• ik ben — я есть/являюсь
• jij bent — ты есть/являешься
• hij/zij/het is — он/она/оно есть
• wij zijn — мы есть/являемся
• jullie zijn — вы есть/являетесь (второе лицо множественного числа)
• zij zijn — они есть/являются

Пример использования:
• Jullie zijn goede vrienden. — Вы хорошие друзья."""

# Example 5: Dutch compound word
EXAMPLE_5_INPUT = "ziekenhuis"
EXAMPLE_5_OUTPUT = """«Ziekenhuis» — существительное, составное слово.
🔑 Артикль: het ziekenhuis (средний род).

Состав: ziek (больной/sick) + en (соединительный элемент) + huis (дом/house).
Буквально: «дом для больных» → больница.

Во множественном числе: de ziekenhuizen.

Пример использования:
• Het ziekenhuis is vlak bij. — Больница совсем рядом."""

# Example 6: Dutch sentence (sentence mode)
EXAMPLE_6_INPUT = "Ik ga morgen naar de markt."
EXAMPLE_6_OUTPUT = """Разбор предложения: «Ik ga morgen naar de markt.»

Пословный глоссарий:
• ik — я (подлежащее)
• ga — иду/еду (гл. gaan, неправильный; сказуемое)
• morgen — завтра (обстоятельство времени)
• naar — в/на (предлог направления)
• de markt — рынок (дополнение с артиклем de)

Структура предложения:
Порядок слов: Subj – V – Adv.времени – Prep.группа (стандартный нидерландский порядок).
Время: настоящее с будущим значением (ga + контекст morgen)."""

# Example 7: Dutch idiom/fixed expression
EXAMPLE_7_INPUT = "voor de hand liggend"
EXAMPLE_7_OUTPUT = """«Voor de hand liggend» — устойчивое выражение (идиома).

Буквальное значение: voor (перед) + de hand (рукой) + liggend (лежащий) = «лежащий перед рукой».
Идиоматическое значение: «очевидный», «само собой разумеющийся», «лежащий на поверхности».

Это фразеологизм, где значение целого выражения отличается от суммы значений его частей.

Пример употребления:
• Het antwoord is voor de hand liggend. — Ответ очевиден."""

OUTPUT_PATH = Path(__file__).parent / "nl_ru_facts.json"


def build_prompt() -> ChatPromptTemplate:
    """Build the Dutch to Russian interesting facts prompt with 7 few-shot examples."""
    return ChatPromptTemplate.from_messages([
        SystemMessage(content=SYSTEM_INSTRUCTION),
        # Example 1: noun with 'de'
        HumanMessage(content=EXAMPLE_1_INPUT),
        AIMessage(content=EXAMPLE_1_OUTPUT),
        # Example 2: noun with 'het'
        HumanMessage(content=EXAMPLE_2_INPUT),
        AIMessage(content=EXAMPLE_2_OUTPUT),
        # Example 3: regular verb with conjugation
        HumanMessage(content=EXAMPLE_3_INPUT),
        AIMessage(content=EXAMPLE_3_OUTPUT),
        # Example 4: irregular verb
        HumanMessage(content=EXAMPLE_4_INPUT),
        AIMessage(content=EXAMPLE_4_OUTPUT),
        # Example 5: compound word
        HumanMessage(content=EXAMPLE_5_INPUT),
        AIMessage(content=EXAMPLE_5_OUTPUT),
        # Example 6: sentence mode
        HumanMessage(content=EXAMPLE_6_INPUT),
        AIMessage(content=EXAMPLE_6_OUTPUT),
        # Example 7: idiom/fixed expression
        HumanMessage(content=EXAMPLE_7_INPUT),
        AIMessage(content=EXAMPLE_7_OUTPUT),
        # Actual input
        MessagesPlaceholder(variable_name="text"),
    ])


if __name__ == "__main__":
    from nl_processing.core.scripts.prompt_author import save_prompt

    save_prompt(build_prompt(), str(OUTPUT_PATH))
