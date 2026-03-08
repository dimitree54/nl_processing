from pathlib import Path
import subprocess
import zipfile

_PROMPT_ARTIFACT = "nl_processing/extract_words_from_text/prompts/nl.json"


def _build_wheel(tmp_path: Path) -> Path:
    package_root = Path(__file__).resolve().parents[3]
    dist_dir = tmp_path / "dist"

    subprocess.run(  # noqa: S603
        ["uv", "build", "--wheel", "--out-dir", str(dist_dir)],
        check=True,
        cwd=package_root,
    )

    return next(dist_dir.glob("nl_processing_extract_words_from_text-*.whl"))


def test_wheel_includes_runtime_prompt_artifact(tmp_path: Path) -> None:
    """The built wheel must ship the prompt artifact used at runtime."""
    wheel_path = _build_wheel(tmp_path)

    with zipfile.ZipFile(wheel_path) as wheel:
        assert _PROMPT_ARTIFACT in wheel.namelist()
