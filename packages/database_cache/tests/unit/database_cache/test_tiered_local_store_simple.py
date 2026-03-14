"""Simple tests for TieredLocalStore basic functionality."""

from nl_processing.database_cache._tiered_local_store import TieredLocalStore  # noqa: F401
from nl_processing.database_cache._tiered_queries import ALL_TIERED_DDL


class TestTieredLocalStoreSimple:
    """Basic tests for TieredLocalStore."""

    def test_import_works(self) -> None:
        """Test that TieredLocalStore can be imported."""
        # Import at top level worked - just check it's available
        assert TieredLocalStore is not None, "TieredLocalStore should be importable"

    def test_queries_available(self) -> None:
        """Test that tiered queries are available."""
        # Import at top level worked - just check the data
        assert len(ALL_TIERED_DDL) > 0, "Tiered DDL should be available"
