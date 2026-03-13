"""Unit tests for functional POS models: preposition, conjunction, pronoun, article, numeral, interjection."""

from nl_processing.extract_word_details._base_models import SharedLearningFields
from nl_processing.extract_word_details.models import (
    NlRuArticleDetails,
    NlRuConjunctionDetails,
    NlRuInterjectionDetails,
    NlRuNumeralDetails,
    NlRuPrepositionDetails,
    NlRuPronounDetails,
)


class TestNlRuPrepositionDetails:
    """Tests for Dutch preposition details model."""

    def test_valid_construction(self, shared_fields: SharedLearningFields) -> None:
        """Test creating a valid preposition details instance."""
        prep = NlRuPrepositionDetails(
            case_governance="Управляет дательным падежом", spatial_or_temporal="Пространственный", shared=shared_fields
        )
        assert prep.case_governance == "Управляет дательным падежом"
        assert prep.spatial_or_temporal == "Пространственный"

    def test_serialization_round_trip(self, shared_fields: SharedLearningFields) -> None:
        """Test model_dump and model_validate round trip."""
        original = NlRuPrepositionDetails(
            case_governance="Предлог направления", spatial_or_temporal="Временной", shared=shared_fields
        )
        data = original.model_dump()
        reconstructed = NlRuPrepositionDetails.model_validate(data)
        assert reconstructed == original


class TestNlRuConjunctionDetails:
    """Tests for Dutch conjunction details model."""

    def test_valid_construction(self, shared_fields: SharedLearningFields) -> None:
        """Test creating a valid conjunction details instance."""
        conj = NlRuConjunctionDetails(
            conjunction_type="Сочинительный союз", word_order_effect="Не влияет на порядок слов", shared=shared_fields
        )
        assert conj.conjunction_type == "Сочинительный союз"
        assert conj.word_order_effect == "Не влияет на порядок слов"

    def test_serialization_round_trip(self, shared_fields: SharedLearningFields) -> None:
        """Test model_dump and model_validate round trip."""
        original = NlRuConjunctionDetails(
            conjunction_type="Подчинительный союз", word_order_effect="Меняет порядок слов", shared=shared_fields
        )
        data = original.model_dump()
        reconstructed = NlRuConjunctionDetails.model_validate(data)
        assert reconstructed == original


class TestNlRuPronounDetails:
    """Tests for Dutch pronoun details model."""

    def test_valid_construction(self, shared_fields: SharedLearningFields) -> None:
        """Test creating a valid pronoun details instance."""
        pron = NlRuPronounDetails(
            pronoun_type="Личное местоимение", declension_forms=["ik", "mij", "me"], shared=shared_fields
        )
        assert pron.pronoun_type == "Личное местоимение"
        assert pron.declension_forms == ["ik", "mij", "me"]

    def test_serialization_round_trip(self, shared_fields: SharedLearningFields) -> None:
        """Test model_dump and model_validate round trip."""
        original = NlRuPronounDetails(
            pronoun_type="Притяжательное местоимение", declension_forms=["mijn", "mijne"], shared=shared_fields
        )
        data = original.model_dump()
        reconstructed = NlRuPronounDetails.model_validate(data)
        assert reconstructed == original


class TestNlRuArticleDetails:
    """Tests for Dutch article details model."""

    def test_valid_construction(self, shared_fields: SharedLearningFields) -> None:
        """Test creating a valid article details instance."""
        art = NlRuArticleDetails(article_type="Определённый артикль", gender_rules="Правила рода", shared=shared_fields)
        assert art.article_type == "Определённый артикль"
        assert art.gender_rules == "Правила рода"

    def test_serialization_round_trip(self, shared_fields: SharedLearningFields) -> None:
        """Test model_dump and model_validate round trip."""
        original = NlRuArticleDetails(
            article_type="Неопределённый артикль", gender_rules="Средний род", shared=shared_fields
        )
        data = original.model_dump()
        reconstructed = NlRuArticleDetails.model_validate(data)
        assert reconstructed == original


class TestNlRuNumeralDetails:
    """Tests for Dutch numeral details model."""

    def test_valid_construction(self, shared_fields: SharedLearningFields) -> None:
        """Test creating a valid numeral details instance."""
        num = NlRuNumeralDetails(
            numeral_type="Количественное числительное", ordinal_form="eerste", shared=shared_fields
        )
        assert num.numeral_type == "Количественное числительное"
        assert num.ordinal_form == "eerste"

    def test_serialization_round_trip(self, shared_fields: SharedLearningFields) -> None:
        """Test model_dump and model_validate round trip."""
        original = NlRuNumeralDetails(numeral_type="Порядковое числительное", ordinal_form=None, shared=shared_fields)
        data = original.model_dump()
        reconstructed = NlRuNumeralDetails.model_validate(data)
        assert reconstructed == original


class TestNlRuInterjectionDetails:
    """Tests for Dutch interjection details model."""

    def test_valid_construction(self, shared_fields: SharedLearningFields) -> None:
        """Test creating a valid interjection details instance."""
        interj = NlRuInterjectionDetails(
            emotion_or_context="Выражает удивление", formality_level="Неформальное", shared=shared_fields
        )
        assert interj.emotion_or_context == "Выражает удивление"
        assert interj.formality_level == "Неформальное"

    def test_serialization_round_trip(self, shared_fields: SharedLearningFields) -> None:
        """Test model_dump and model_validate round trip."""
        original = NlRuInterjectionDetails(
            emotion_or_context="Выражает боль", formality_level="Нейтральное", shared=shared_fields
        )
        data = original.model_dump()
        reconstructed = NlRuInterjectionDetails.model_validate(data)
        assert reconstructed == original
