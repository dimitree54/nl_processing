import pytest

from nl_processing.core.exceptions import (
    APIError,
    TargetLanguageNotFoundError,
    UnsupportedImageFormatError,
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


def test_target_language_not_found_error_can_be_raised_and_caught() -> None:
    """Test TargetLanguageNotFoundError can be raised and caught."""
    with pytest.raises(TargetLanguageNotFoundError):
        raise TargetLanguageNotFoundError("no Dutch")


def test_target_language_not_found_error_preserves_message() -> None:
    """Test TargetLanguageNotFoundError preserves message string."""
    error = TargetLanguageNotFoundError("no Dutch text found")
    assert str(error) == "no Dutch text found"


def test_unsupported_image_format_error_can_be_raised_and_caught() -> None:
    """Test UnsupportedImageFormatError can be raised and caught."""
    with pytest.raises(UnsupportedImageFormatError):
        raise UnsupportedImageFormatError(".bmp")


def test_unsupported_image_format_error_preserves_message() -> None:
    """Test UnsupportedImageFormatError preserves message string."""
    error = UnsupportedImageFormatError(".bmp format not supported")
    assert str(error) == ".bmp format not supported"


def test_all_exceptions_are_subclasses_of_exception() -> None:
    """Test all exceptions are subclasses of Exception."""
    assert issubclass(APIError, Exception)
    assert issubclass(TargetLanguageNotFoundError, Exception)
    assert issubclass(UnsupportedImageFormatError, Exception)


def test_exceptions_are_distinct_types() -> None:
    """Test exceptions are distinct types - catching one does not catch another."""
    # APIError does not catch TargetLanguageNotFoundError
    with pytest.raises(TargetLanguageNotFoundError):
        try:
            raise TargetLanguageNotFoundError("test")
        except APIError:
            pytest.fail("APIError should not catch TargetLanguageNotFoundError")

    # APIError does not catch UnsupportedImageFormatError
    with pytest.raises(UnsupportedImageFormatError):
        try:
            raise UnsupportedImageFormatError("test")
        except APIError:
            pytest.fail("APIError should not catch UnsupportedImageFormatError")

    # TargetLanguageNotFoundError does not catch UnsupportedImageFormatError
    with pytest.raises(UnsupportedImageFormatError):
        try:
            raise UnsupportedImageFormatError("test")
        except TargetLanguageNotFoundError:
            pytest.fail("TargetLanguageNotFoundError should not catch UnsupportedImageFormatError")


def test_exceptions_accept_empty_message() -> None:
    """Test exceptions accept empty message string."""
    api_error = APIError("")
    target_error = TargetLanguageNotFoundError("")
    format_error = UnsupportedImageFormatError("")

    assert str(api_error) == ""
    assert str(target_error) == ""
    assert str(format_error) == ""


def test_exceptions_accept_no_args() -> None:
    """Test exceptions accept no-args construction."""
    api_error = APIError()
    target_error = TargetLanguageNotFoundError()
    format_error = UnsupportedImageFormatError()

    assert str(api_error) == ""
    assert str(target_error) == ""
    assert str(format_error) == ""
