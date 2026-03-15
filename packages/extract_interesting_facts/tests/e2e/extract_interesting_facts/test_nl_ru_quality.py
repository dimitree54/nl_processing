from nl_processing.core.models import Language
import pytest

from nl_processing.extract_interesting_facts.service import InterestingFactsExtractor
from tests.e2e.extract_interesting_facts.assertions import assert_contains_any, assert_no_llm_chatter


@pytest.mark.asyncio
async def test_noun_de_article_and_pos() -> None:
    """Dutch noun 'hond' shows 'de' article, part of speech, and usage example."""
    extractor = InterestingFactsExtractor(source_language=Language.NL, target_language=Language.RU)
    result = await extractor.extract("hond")

    assert len(result) > 0, "Result should not be empty"
    assert_no_llm_chatter(result)
    assert_contains_any(result, ["de"], "article check")
    assert_contains_any(result, ["существительное", "noun", "Существительное"], "part of speech")
    assert_contains_any(result, ["пример", "Пример", "употребл"], "usage note")


@pytest.mark.asyncio
async def test_noun_het_article() -> None:
    """Dutch noun 'huis' shows 'het' article."""
    extractor = InterestingFactsExtractor(source_language=Language.NL, target_language=Language.RU)
    result = await extractor.extract("huis")

    assert len(result) > 0, "Result should not be empty"
    assert_no_llm_chatter(result)
    assert_contains_any(result, ["het"], "het article")


@pytest.mark.asyncio
async def test_verb_conjugation_and_regularity() -> None:
    """Dutch verb 'werken' shows jullie form and regularity statement."""
    extractor = InterestingFactsExtractor(source_language=Language.NL, target_language=Language.RU)
    result = await extractor.extract("werken")

    assert len(result) > 0, "Result should not be empty"
    assert_no_llm_chatter(result)
    assert_contains_any(result, ["jullie"], "second person plural check")
    assert_contains_any(result, ["правильный", "правильн", "Правильный", "regelmatig"], "regularity statement")


@pytest.mark.asyncio
async def test_compound_word_decomposition() -> None:
    """Dutch compound 'ziekenhuis' identifies meaningful parts."""
    extractor = InterestingFactsExtractor(source_language=Language.NL, target_language=Language.RU)
    result = await extractor.extract("ziekenhuis")

    assert len(result) > 0, "Result should not be empty"
    assert_no_llm_chatter(result)
    assert_contains_any(result, ["ziek", "huis", "состав", "части"], "composition mention")


@pytest.mark.asyncio
async def test_sentence_mode_lighter_per_token() -> None:
    """Sentence mode provides token glosses without full lexical dossiers."""
    extractor = InterestingFactsExtractor(source_language=Language.NL, target_language=Language.RU)
    result = await extractor.extract("Ik ga morgen naar de markt.")

    assert len(result) > 0, "Result should not be empty"
    assert_no_llm_chatter(result)
    assert_contains_any(result, ["ik", "ga", "morgen"], "token glosses")
    assert len(result) < 1500, "Response should be lighter than full lexical mode"


@pytest.mark.asyncio
async def test_idiom_identified() -> None:
    """Idiom 'voor de hand liggend' is identified as an expression/idiom."""
    extractor = InterestingFactsExtractor(source_language=Language.NL, target_language=Language.RU)
    result = await extractor.extract("voor de hand liggend")

    assert len(result) > 0, "Result should not be empty"
    assert_no_llm_chatter(result)
    assert_contains_any(
        result,
        [
            "устойчивое выражение",
            "фразеологизм",
            "идиоматическое выражение",
            "идиома",
            "переносн",
            "фразеологи",
            "устойчив",
            "фиксированное выражение",
            "выражение",
            "значение отличается",
            "буквального значения",
        ],
        "idiom identification",
    )


@pytest.mark.asyncio
async def test_multi_sentence_not_rejected() -> None:
    """Multi-sentence input is processed without rejection."""
    extractor = InterestingFactsExtractor(source_language=Language.NL, target_language=Language.RU)
    # Should not raise ValueError or APIError
    result = await extractor.extract("De hond loopt in het park. Het is een mooie dag.")
    assert len(result) > 0, "Result should not be empty"
