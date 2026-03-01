def extract_text_from_image(image_path: str) -> str:
    file_name = image_path.rsplit("/", maxsplit=1)[-1]
    return f"mock extracted text from {file_name}"
