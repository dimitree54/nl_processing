from collections.abc import Callable
import json
from pathlib import Path

from langchain_core.load import dumpd
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel
import pytest

from nl_processing.core.models import Language
from nl_processing.core.prompts import build_translation_chain

_BUILD_TRANSLATION_CHAIN: Callable[..., object] = build_translation_chain


class _DummyToolSchema(BaseModel):
    word: str


def _write_prompt_file(prompts_dir: Path, source: Language, target: Language) -> None:
    """Create a prompt JSON file for the given language pair."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Translate from {source_lang} to {target_lang}."),
        ("human", "{text}"),
    ])
    filename = f"{source.value}_{target.value}.json"
    (prompts_dir / filename).write_text(json.dumps(dumpd(prompt)))


class _SpyChatOpenAI:
    """Spy that records constructor args and returns a _FakeBoundLLM."""

    instances: list["_SpyChatOpenAI"] = []

    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.bind_tools_calls: list[tuple[list[object], str]] = []
        _SpyChatOpenAI.instances.append(self)

    def bind_tools(self, tools: list[object], tool_choice: str) -> RunnableLambda:
        self.bind_tools_calls.append((tools, tool_choice))
        return RunnableLambda(lambda _x: None)


@pytest.fixture(autouse=True)
def _patch_chat_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    _SpyChatOpenAI.instances = []
    monkeypatch.setattr("nl_processing.core.prompts.ChatOpenAI", _SpyChatOpenAI)


def test_returns_chain(tmp_path: Path) -> None:
    """Test build_translation_chain returns a prompt|llm chain."""
    _write_prompt_file(tmp_path, Language.NL, Language.RU)

    chain = _BUILD_TRANSLATION_CHAIN(
        source_language=Language.NL,
        target_language=Language.RU,
        prompts_dir=tmp_path,
        tool_schema=_DummyToolSchema,
        model="gpt-4o-mini",
    )

    assert chain is not None


def test_constructs_correct_prompt_filename(tmp_path: Path) -> None:
    """Test build_translation_chain loads prompt from <source>_<target>.json."""
    _write_prompt_file(tmp_path, Language.RU, Language.NL)

    chain = _BUILD_TRANSLATION_CHAIN(
        source_language=Language.RU,
        target_language=Language.NL,
        prompts_dir=tmp_path,
        tool_schema=_DummyToolSchema,
        model="gpt-4o-mini",
    )

    assert chain is not None


def test_passes_model_params(tmp_path: Path) -> None:
    """Test build_translation_chain passes model, temperature, reasoning_effort, service_tier."""
    _write_prompt_file(tmp_path, Language.NL, Language.RU)

    _BUILD_TRANSLATION_CHAIN(
        source_language=Language.NL,
        target_language=Language.RU,
        prompts_dir=tmp_path,
        tool_schema=_DummyToolSchema,
        model="gpt-4o",
        temperature=0.5,
        reasoning_effort="high",
        service_tier="default",
    )

    spy = _SpyChatOpenAI.instances[0]
    assert spy.kwargs == {
        "model": "gpt-4o",
        "temperature": 0.5,
        "reasoning_effort": "high",
        "service_tier": "default",
    }


def test_binds_tool_schema(tmp_path: Path) -> None:
    """Test build_translation_chain binds tool_schema with tool_choice."""
    _write_prompt_file(tmp_path, Language.NL, Language.RU)

    _BUILD_TRANSLATION_CHAIN(
        source_language=Language.NL,
        target_language=Language.RU,
        prompts_dir=tmp_path,
        tool_schema=_DummyToolSchema,
        model="gpt-4o-mini",
    )

    spy = _SpyChatOpenAI.instances[0]
    assert len(spy.bind_tools_calls) == 1
    tools, tool_choice = spy.bind_tools_calls[0]
    assert tools == [_DummyToolSchema]
    assert tool_choice == "_DummyToolSchema"


def test_missing_prompt_file(tmp_path: Path) -> None:
    """Test build_translation_chain raises FileNotFoundError from prompt-file access when absent."""
    with pytest.raises(FileNotFoundError):
        _BUILD_TRANSLATION_CHAIN(
            source_language=Language.NL,
            target_language=Language.RU,
            prompts_dir=tmp_path,
            tool_schema=_DummyToolSchema,
            model="gpt-4o-mini",
        )


def test_default_temperature(tmp_path: Path) -> None:
    """Test build_translation_chain defaults temperature to 0."""
    _write_prompt_file(tmp_path, Language.NL, Language.RU)

    _BUILD_TRANSLATION_CHAIN(
        source_language=Language.NL,
        target_language=Language.RU,
        prompts_dir=tmp_path,
        tool_schema=_DummyToolSchema,
        model="gpt-4o-mini",
    )

    spy = _SpyChatOpenAI.instances[0]
    assert spy.kwargs["temperature"] == 0
    assert spy.kwargs["reasoning_effort"] is None
    assert spy.kwargs["service_tier"] is None
