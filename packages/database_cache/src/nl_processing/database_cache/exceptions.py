class CacheNotReadyError(Exception):
    """Raised when cached data is requested before the first usable snapshot exists."""


class CacheStorageError(Exception):
    """Raised when the local SQLite cache file cannot be opened, read, or updated."""


class CacheSyncError(Exception):
    """Raised when an explicit refresh or flush operation fails synchronously."""
