from pathlib import Path
import subprocess
import zipfile

import pytest


_PROMPT_ARTIFACTS = [
    "nl_processing/extract_text_from_image/prompts/nl.json",
    "nl_processing/extract_words_from_text/prompts/nl.json",
    "nl_processing/translate_text/prompts/nl_ru.json",
    "nl_processing/translate_word/prompts/nl_ru.json",
]


def _build_wheel(tmp_path: Path) -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    dist_dir = tmp_path / "dist"

    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(dist_dir)],
        check=True,
        cwd=repo_root,
    )

    return next(dist_dir.glob("nl_processing-*.whl"))


@pytest.mark.parametrize("prompt_artifact", _PROMPT_ARTIFACTS)
def test_wheel_includes_runtime_prompt_artifacts(tmp_path: Path, prompt_artifact: str) -> None:
    """The built wheel must ship every prompt artifact used at runtime."""
    wheel_path = _build_wheel(tmp_path)

    with zipfile.ZipFile(wheel_path) as wheel:
        assert prompt_artifact in wheel.namelist()
