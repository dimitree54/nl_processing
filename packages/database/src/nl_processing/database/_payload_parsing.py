"""Payload parsing utilities for detailed word store operations."""

import json

from nl_processing.database.detailed_models import JsonValue


def parse_payload_from_backend(payload_raw: str | dict | object) -> dict[str, JsonValue]:
    """Parse payload from backend response, handling both JSON string and dict formats.

    Args:
        payload_raw: Raw payload from backend (JSON string from mock, dict from real backend)

    Returns:
        Parsed payload as JsonValue dict

    Raises:
        TypeError: If payload_raw is neither string nor dict
    """
    if isinstance(payload_raw, str):
        # Mock backend stores as JSON string
        return json.loads(payload_raw)
    elif isinstance(payload_raw, dict):
        # Real backend returns dict directly (asyncpg JSONB deserialization)
        return payload_raw
    else:
        # Fallback for unexpected types (should not happen in practice)
        raise TypeError(f"Unexpected payload type: {type(payload_raw)}")
