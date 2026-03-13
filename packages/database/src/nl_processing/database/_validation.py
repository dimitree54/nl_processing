"""Validation helper for detailed word store operations."""

from nl_processing.database.detailed_models import JsonValue
from nl_processing.database.detailed_ports import PayloadValidatorPort


def validate_payload_if_configured(
    payload_validator: PayloadValidatorPort | None,
    schema_key: str,
    schema_version: int,
    payload: dict[str, JsonValue],
) -> None:
    """Validate payload if validator is configured."""
    if payload_validator is not None:
        payload_validator.validate_payload(schema_key, schema_version, payload)
