import pytest

from nl_processing.core.exceptions import (
    APIError,
    TargetLanguageNotFoundInInputError,
    UnsupportedImageFormatError,
    UnsupportedLanguageError,
)


def test_api_error_can_be_raised_and_caught() -> None:
    """Test APIError can be raised and caught."""
    with pytest.raises(APIError):
        raise APIError("test")


def test_api_error_preserves_message() -> None:
    """Test APIError preserves message string."""
    error = APIError("test message")
    assert str(error) == "test message"


def test_api_error_can_wrap_exception() -> None:
    """Test APIError can wrap another exception via raise from."""
    original = ValueError("original error")
    try:
        raise APIError("wrapped") from original
    except APIError as e:
        assert e.__cause__ is original
        assert str(e) == "wrapped"
        assert str(e.__cause__) == "original error"


def test_unsupported_image_format_error_can_be_raised_and_caught() -> None:
    """Test UnsupportedImageFormatError can be raised and caught."""
    with pytest.raises(UnsupportedImageFormatError):
        raise UnsupportedImageFormatError(".bmp")


def test_unsupported_image_format_error_preserves_message() -> None:
    """Test UnsupportedImageFormatError preserves message string."""
    error = UnsupportedImageFormatError(".bmp format not supported")
    assert str(error) == ".bmp format not supported"


def test_target_language_not_found_in_input_error_can_be_raised_and_caught() -> None:
    """Test TargetLanguageNotFoundInInputError can be raised and caught."""
    with pytest.raises(TargetLanguageNotFoundInInputError):
        raise TargetLanguageNotFoundInInputError("expected Dutch input")


def test_target_language_not_found_in_input_error_preserves_message() -> None:
    """Test TargetLanguageNotFoundInInputError preserves message string."""
    error = TargetLanguageNotFoundInInputError("expected Dutch input")
    assert str(error) == "expected Dutch input"


def test_unsupported_language_error_can_be_raised_and_caught() -> None:
    """Test UnsupportedLanguageError can be raised and caught."""
    with pytest.raises(UnsupportedLanguageError):
        raise UnsupportedLanguageError("ru")


def test_unsupported_language_error_preserves_message() -> None:
    """Test UnsupportedLanguageError preserves message string."""
    error = UnsupportedLanguageError("ru is not supported")
    assert str(error) == "ru is not supported"


def test_all_exceptions_are_subclasses_of_exception() -> None:
    """Test all exceptions are subclasses of Exception."""
    assert issubclass(APIError, Exception)
    assert issubclass(UnsupportedImageFormatError, Exception)
    assert issubclass(TargetLanguageNotFoundInInputError, Exception)
    assert issubclass(UnsupportedLanguageError, Exception)


def test_runtime_and_initialization_language_errors_have_expected_base_types() -> None:
    """Test language-related errors distinguish runtime from initialization failures."""
    assert issubclass(TargetLanguageNotFoundInInputError, RuntimeError)
    assert not issubclass(TargetLanguageNotFoundInInputError, ValueError)
    assert issubclass(UnsupportedLanguageError, ValueError)
    assert not issubclass(UnsupportedLanguageError, RuntimeError)


def test_exceptions_are_distinct_types() -> None:
    """Test exceptions are distinct types where catch boundaries are expected to stay separate."""
    # APIError does not catch UnsupportedImageFormatError
    with pytest.raises(UnsupportedImageFormatError):
        try:
            raise UnsupportedImageFormatError("test")
        except APIError:
            pytest.fail("APIError should not catch UnsupportedImageFormatError")

    # Runtime input-language failure does not catch initialization-language failure
    with pytest.raises(UnsupportedLanguageError):
        try:
            raise UnsupportedLanguageError("test")
        except TargetLanguageNotFoundInInputError:
            pytest.fail("TargetLanguageNotFoundInInputError should not catch UnsupportedLanguageError")

    # UnsupportedImageFormatError does not catch UnsupportedLanguageError
    with pytest.raises(UnsupportedLanguageError):
        try:
            raise UnsupportedLanguageError("test")
        except UnsupportedImageFormatError:
            pytest.fail("UnsupportedImageFormatError should not catch UnsupportedLanguageError")


def test_exceptions_accept_empty_message() -> None:
    """Test exceptions accept empty message string."""
    api_error = APIError("")
    format_error = UnsupportedImageFormatError("")
    missing_input_language_error = TargetLanguageNotFoundInInputError("")
    language_error = UnsupportedLanguageError("")

    assert str(api_error) == ""
    assert str(format_error) == ""
    assert str(missing_input_language_error) == ""
    assert str(language_error) == ""


def test_exceptions_accept_no_args() -> None:
    """Test exceptions accept no-args construction."""
    api_error = APIError()
    format_error = UnsupportedImageFormatError()
    missing_input_language_error = TargetLanguageNotFoundInInputError()
    language_error = UnsupportedLanguageError()

    assert str(api_error) == ""
    assert str(format_error) == ""
    assert str(missing_input_language_error) == ""
    assert str(language_error) == ""
