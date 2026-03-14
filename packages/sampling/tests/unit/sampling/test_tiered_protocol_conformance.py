"""Protocol conformance tests for TieredExerciseSampler mocks."""

from tests.unit.sampling.tiered_conftest import mock_provider_satisfies_protocol


def test_mock_provider_satisfies_protocol() -> None:
    """MockTieredCandidateProvider structurally satisfies TieredCandidateProvider."""
    assert mock_provider_satisfies_protocol()
