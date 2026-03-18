"""Unit tests for abstract backend interface."""

from abc import ABC

import pytest

from nl_processing.database_core.backend.abstract import AbstractBackend


def test_abstract_backend_is_abstract() -> None:
    """AbstractBackend should be an abstract base class."""
    assert issubclass(AbstractBackend, ABC)


def test_abstract_backend_cannot_be_instantiated() -> None:
    """AbstractBackend should not be instantiable."""
    with pytest.raises(TypeError):
        AbstractBackend()  # type: ignore


def test_abstract_backend_has_required_methods() -> None:
    """AbstractBackend should define all required abstract methods."""
    # Check that the abstract methods exist
    abstract_methods = AbstractBackend.__abstractmethods__
    expected_methods = {
        "create_background_backend",
        "add_word",
        "get_word",
        "add_translation_link",
        "get_user_words",
        "count_user_words",
        "add_user_word",
        "increment_user_exercise_score",
        "get_user_exercise_scores",
        "apply_score_delta_atomic",
        "create_tables",
        "check_user_word_exists",
        "delete_user_word",
        "delete_user_exercise_score",
        "upsert_word_details",
        "get_word_details",
        "get_word_details_batch",
    }

    # Check that all expected methods are abstract
    for method in expected_methods:
        assert method in abstract_methods, f"Method {method} should be abstract"
