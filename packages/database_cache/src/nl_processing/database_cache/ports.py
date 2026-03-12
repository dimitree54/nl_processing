"""Port protocols for remote operations not covered by core.ports."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class RemoteDeletePort(Protocol):
    """Remote delete contract consumed by the cache for remote-first deletes."""

    async def delete_word(self, source_word_id: int, exercise_types: list[str] | None = None) -> None: ...

    async def delete_words(self, source_word_ids: list[int], exercise_types: list[str] | None = None) -> None: ...
