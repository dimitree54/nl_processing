import inspect
import json

from langchain_core.load import dumpd
from langchain_core.prompts import ChatPromptTemplate
from nl_processing.core.prompts import load_prompt

from nl_processing.translate_text_from_image.prompts.generate_nl_ru_prompt import build_prompt
import nl_processing.translate_text_from_image.service as service_module
from nl_processing.translate_text_from_image.service import _PROMPTS_DIR, _SUPPORTED_PAIRS


def test_prompt_asset_exists_and_loads() -> None:
    """Verifies the nl_ru.json prompt asset exists and loads correctly."""
    # Check prompt directory structure
    expected_prompt_path = _PROMPTS_DIR / "nl_ru.json"
    assert expected_prompt_path.exists(), f"Prompt file missing at {expected_prompt_path}"

    # Validate prompt loading functionality
    loaded_prompt = load_prompt(str(expected_prompt_path))
    assert isinstance(loaded_prompt, ChatPromptTemplate), "Should load as ChatPromptTemplate instance"


def test_prompt_generator_reproduces_committed_artifact() -> None:
    """Confirms the prompt generator produces content matching committed nl_ru.json."""
    # Generate prompt using the build function
    generated_prompt = build_prompt()

    # Serialize to match committed format
    generated_data = dumpd(generated_prompt)

    # Load committed artifact
    committed_path = _PROMPTS_DIR / "nl_ru.json"
    with open(committed_path, encoding="utf-8") as f:
        committed_data = json.load(f)

    # Verify content equivalence
    assert generated_data == committed_data, "Generated prompt should match committed artifact"


def test_supported_pairs_match_prompt_files() -> None:
    """Validates that each supported language pair has corresponding prompt file."""
    # Check each supported pair has its prompt file
    for source_lang, target_lang in _SUPPORTED_PAIRS:
        expected_filename = f"{source_lang}_{target_lang}.json"
        prompt_file_path = _PROMPTS_DIR / expected_filename

        file_exists = prompt_file_path.exists()
        assert file_exists, f"Missing prompt file for {source_lang}->{target_lang}: {expected_filename}"


def test_service_uses_core_image_helpers() -> None:
    """Confirms service module imports and uses core image encoding utilities."""
    # Get service module source code
    service_source = inspect.getsource(service_module)

    # Verify core image encoding import
    core_import_present = "nl_processing.core.image_encoding" in service_source
    assert core_import_present, "Service should import from nl_processing.core.image_encoding"

    # Check for specific core function usage
    expected_functions = ["encode_cv2_to_base64", "encode_path_to_base64", "validate_image_format"]

    for func_name in expected_functions:
        function_used = func_name in service_source
        assert function_used, f"Service should use {func_name} from core.image_encoding"
