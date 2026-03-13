"""Unit tests for base models and shared learning fields."""

from nl_processing.extract_word_details._base_models import (
    CommonPhrase,
    ExampleSentence,
    InterestingFact,
    SharedLearningFields,
    WordPartExplanation,
)


class TestCommonPhrase:
    """Test CommonPhrase model."""

    def test_construction(self) -> None:
        phrase = CommonPhrase(phrase="op tijd", translation="вовремя")

        assert phrase.phrase == "op tijd"
        assert phrase.translation == "вовремя"

    def test_serialization(self) -> None:
        phrase = CommonPhrase(phrase="op tijd", translation="вовремя")

        data = phrase.model_dump()
        expected = {"phrase": "op tijd", "translation": "вовремя"}

        assert data == expected


class TestExampleSentence:
    """Test ExampleSentence model."""

    def test_construction(self) -> None:
        sentence = ExampleSentence(dutch_sentence="Ik kom op tijd.", russian_explanation="Я прихожу вовремя.")

        assert sentence.dutch_sentence == "Ik kom op tijd."
        assert sentence.russian_explanation == "Я прихожу вовремя."

    def test_serialization(self) -> None:
        sentence = ExampleSentence(dutch_sentence="Ik kom op tijd.", russian_explanation="Я прихожу вовремя.")

        data = sentence.model_dump()
        expected = {"dutch_sentence": "Ik kom op tijd.", "russian_explanation": "Я прихожу вовремя."}

        assert data == expected


class TestWordPartExplanation:
    """Test WordPartExplanation model."""

    def test_construction(self) -> None:
        part = WordPartExplanation(part="tijd", explanation_russian="время")

        assert part.part == "tijd"
        assert part.explanation_russian == "время"

    def test_serialization(self) -> None:
        part = WordPartExplanation(part="tijd", explanation_russian="время")

        data = part.model_dump()
        expected = {"part": "tijd", "explanation_russian": "время"}

        assert data == expected


class TestInterestingFact:
    """Test InterestingFact model."""

    def test_construction_with_parallel(self) -> None:
        fact = InterestingFact(
            fact_russian="В голландском языке время очень важно",
            dutch_parallel="In het Nederlands is tijd heel belangrijk",
        )

        assert fact.fact_russian == "В голландском языке время очень важно"
        assert fact.dutch_parallel == "In het Nederlands is tijd heel belangrijk"

    def test_construction_without_parallel(self) -> None:
        fact = InterestingFact(fact_russian="В голландском языке время очень важно")

        assert fact.fact_russian == "В голландском языке время очень важно"
        assert fact.dutch_parallel is None

    def test_serialization(self) -> None:
        fact = InterestingFact(
            fact_russian="В голландском языке время очень важно",
            dutch_parallel="In het Nederlands is tijd heel belangrijk",
        )

        data = fact.model_dump()
        expected = {
            "fact_russian": "В голландском языке время очень важно",
            "dutch_parallel": "In het Nederlands is tijd heel belangrijk",
        }

        assert data == expected


class TestSharedLearningFields:
    """Test SharedLearningFields model."""

    def test_construction_with_empty_lists(self) -> None:
        fields = SharedLearningFields(common_phrases=[], example_sentences=[], word_parts=[], interesting_facts=[])

        assert fields.common_phrases == []
        assert fields.example_sentences == []
        assert fields.word_parts == []
        assert fields.interesting_facts == []

    def test_construction_with_populated_lists(self) -> None:
        phrase = CommonPhrase(phrase="op tijd", translation="вовремя")
        sentence = ExampleSentence(dutch_sentence="Ik kom op tijd.", russian_explanation="Я прихожу вовремя.")
        part = WordPartExplanation(part="tijd", explanation_russian="время")
        fact = InterestingFact(fact_russian="В голландском языке время очень важно")

        fields = SharedLearningFields(
            common_phrases=[phrase], example_sentences=[sentence], word_parts=[part], interesting_facts=[fact]
        )

        assert len(fields.common_phrases) == 1
        assert len(fields.example_sentences) == 1
        assert len(fields.word_parts) == 1
        assert len(fields.interesting_facts) == 1

        assert fields.common_phrases[0] == phrase
        assert fields.example_sentences[0] == sentence
        assert fields.word_parts[0] == part
        assert fields.interesting_facts[0] == fact

    def test_serialization_round_trip(self) -> None:
        phrase = CommonPhrase(phrase="op tijd", translation="вовремя")
        sentence = ExampleSentence(dutch_sentence="Ik kom op tijd.", russian_explanation="Я прихожу вовремя.")
        part = WordPartExplanation(part="tijd", explanation_russian="время")
        fact = InterestingFact(
            fact_russian="В голландском языке время очень важно",
            dutch_parallel="In het Nederlands is tijd heel belangrijk",
        )

        original = SharedLearningFields(
            common_phrases=[phrase], example_sentences=[sentence], word_parts=[part], interesting_facts=[fact]
        )

        data = original.model_dump()
        reconstructed = SharedLearningFields.model_validate(data)

        assert reconstructed == original
