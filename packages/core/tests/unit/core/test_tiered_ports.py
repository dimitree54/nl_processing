from nl_processing.core.models import Language, PartOfSpeech, Word, WordPair
from nl_processing.core.tiered_models import TieredCandidate, TieredSnapshotEntry
from nl_processing.core.tiered_ports import (
    RemoteTieredSyncPort,
    TieredCandidateProvider,
)


class MockTieredCandidateProvider:
    """Mock implementation of TieredCandidateProvider."""

    async def get_tiered_candidates(self) -> list[TieredCandidate]:
        word_pair = WordPair(
            source=Word(normalized_form="test", word_type=PartOfSpeech.NOUN, language=Language.NL),
            target=Word(normalized_form="test", word_type=PartOfSpeech.NOUN, language=Language.RU),
        )
        return [
            TieredCandidate(
                pair=word_pair,
                source_word_id=1,
                scores={"translate": 2},
                in_repeat_mode=False,
            )
        ]


class MockRemoteTieredSyncPort:
    """Mock implementation of RemoteTieredSyncPort."""

    async def export_tiered_snapshot(self) -> list[TieredSnapshotEntry]:
        word_pair = WordPair(
            source=Word(normalized_form="test", word_type=PartOfSpeech.NOUN, language=Language.NL),
            target=Word(normalized_form="test", word_type=PartOfSpeech.NOUN, language=Language.RU),
        )
        return [
            TieredSnapshotEntry(
                source_word_id=1,
                target_word_id=2,
                pair=word_pair,
                scores={"translate": 3},
                in_repeat_mode=False,
            )
        ]

    async def apply_tiered_result(self, *, event_id: str, source_word_id: int, exercise_type: str, delta: int) -> None:
        pass


class NonConformingProvider:
    """Class that does not implement TieredCandidateProvider."""

    def some_other_method(self) -> str:
        return "not a provider"


class NonConformingSyncPort:
    """Class that does not implement RemoteTieredSyncPort."""

    def some_other_method(self) -> str:
        return "not a sync port"


def test_tiered_candidate_provider_protocol_conformance() -> None:
    """Test TieredCandidateProvider protocol conformance check passes."""
    provider = MockTieredCandidateProvider()
    assert isinstance(provider, TieredCandidateProvider)


def test_tiered_candidate_provider_protocol_non_conformance() -> None:
    """Test TieredCandidateProvider protocol conformance check fails for non-conforming class."""
    non_provider = NonConformingProvider()
    assert not isinstance(non_provider, TieredCandidateProvider)


def test_remote_tiered_sync_port_protocol_conformance() -> None:
    """Test RemoteTieredSyncPort protocol conformance check passes."""
    sync_port = MockRemoteTieredSyncPort()
    assert isinstance(sync_port, RemoteTieredSyncPort)


def test_remote_tiered_sync_port_protocol_non_conformance() -> None:
    """Test RemoteTieredSyncPort protocol conformance check fails for non-conforming class."""
    non_sync_port = NonConformingSyncPort()
    assert not isinstance(non_sync_port, RemoteTieredSyncPort)
