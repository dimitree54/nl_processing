from nl_processing import extract_text_from_image


def test_extract_text_from_image_returns_mock_text() -> None:
    text = extract_text_from_image("/tmp/input_photo.png")
    assert text == "mock extracted text from input_photo.png"
