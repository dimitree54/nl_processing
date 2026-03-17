"""Integration test seeding helpers for database tests against real Neon."""

from dataclasses import dataclass
import json
import uuid

from nl_processing.core.models import Language, PartOfSpeech
from nl_processing.database_core.backend.neon import NeonBackend


@dataclass
class SeededWordPair:
    """Result from seeding a word pair."""

    source_word_id: int
    target_word_id: int | None
    user_id: str
    source_normalized_form: str
    target_normalized_form: str | None
    word_type: PartOfSpeech


async def seed_word_pair(
    backend: NeonBackend,
    user_id: str,
    source_form: str,
    target_form: str | None = None,
    word_type: PartOfSpeech = PartOfSpeech.NOUN,
    source_language: Language = Language.NL,
    target_language: Language = Language.RU,
) -> SeededWordPair:
    """Seed a single word pair with optional translation link."""
    # Add source word
    source_word_id = await backend.add_word(source_language.value, source_form, word_type.value)
    if source_word_id is None:
        source_dict = await backend.get_word(source_language.value, source_form)
        source_word_id = int(source_dict["id"])

    # Add user membership for source word
    await backend.add_user_word(user_id, source_word_id, source_language.value)

    target_word_id = None
    if target_form is not None:
        # Add target word
        target_word_id = await backend.add_word(target_language.value, target_form, word_type.value)
        if target_word_id is None:
            target_dict = await backend.get_word(target_language.value, target_form)
            target_word_id = int(target_dict["id"])

        # Add translation link
        table_name = f"{source_language.value}_{target_language.value}"
        await backend.add_translation_link(table_name, source_word_id, target_word_id)

    return SeededWordPair(
        source_word_id=source_word_id,
        target_word_id=target_word_id,
        user_id=user_id,
        source_normalized_form=source_form,
        target_normalized_form=target_form,
        word_type=word_type,
    )


async def seed_word_set(
    backend: NeonBackend,
    user_id: str,
    word_specs: list[tuple[str, str | None, PartOfSpeech]],
    source_language: Language = Language.NL,
    target_language: Language = Language.RU,
) -> list[SeededWordPair]:
    """Seed multiple word pairs for one user in a single call.

    Each word_spec is (source_form, target_form_or_none, word_type).
    """
    results = []
    for source_form, target_form, word_type in word_specs:
        pair = await seed_word_pair(
            backend=backend,
            user_id=user_id,
            source_form=source_form,
            target_form=target_form,
            word_type=word_type,
            source_language=source_language,
            target_language=target_language,
        )
        results.append(pair)
    return results


async def seed_scores(
    backend: NeonBackend,
    source_word_id: int,
    user_id: str,
    scores: dict[str, int],
    source_language: Language = Language.NL,
    target_language: Language = Language.RU,
) -> None:
    """Attach exercise scores to a seeded source word."""
    for exercise_type, score in scores.items():
        table_name = f"{source_language.value}_{target_language.value}_{exercise_type}"
        await backend.increment_user_exercise_score(table_name, user_id, source_word_id, score)


async def seed_detail_row(
    backend: NeonBackend,
    source_word_id: int,
    word_type: PartOfSpeech,
    schema_key: str,
    schema_version: int,
    payload: dict,
    source_language: Language = Language.NL,
    target_language: Language = Language.RU,
) -> None:
    """Persist one detailed-word row for a canonical source word."""
    table_name = f"word_details_{source_language.value}_{target_language.value}"

    await backend.upsert_word_details(
        table=table_name,
        source_word_id=source_word_id,
        word_type=word_type.value,
        schema_key=schema_key,
        schema_version=schema_version,
        payload=json.dumps(payload),
    )


def make_unique_user_id() -> str:
    """Generate a unique user ID for test isolation."""
    return f"test_user_{uuid.uuid4().hex[:8]}"


def make_unique_word_form(base: str) -> str:
    """Generate a unique word form for test isolation."""
    return f"{base}_{uuid.uuid4().hex[:6]}"
