"""Unit tests for runtime_checkable protocols in database_cache."""

from nl_processing.database_cache.detailed_ports import RemoteDetailedWordStorePort, SchemaVersionChecker
from tests.unit.database_cache.detailed_mocks import MockRemoteDetailedWordStore, MockSchemaChecker


def test_mock_remote_store_satisfies_protocol() -> None:
    assert isinstance(MockRemoteDetailedWordStore([]), RemoteDetailedWordStorePort)


def test_mock_schema_checker_satisfies_protocol() -> None:
    assert isinstance(MockSchemaChecker({}), SchemaVersionChecker)


def test_non_conforming_class_fails_remote_store_check() -> None:
    assert not isinstance(object(), RemoteDetailedWordStorePort)


def test_non_conforming_class_fails_schema_checker_check() -> None:
    assert not isinstance(object(), SchemaVersionChecker)
