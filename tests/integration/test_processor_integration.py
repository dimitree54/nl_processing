from nl_processing import MockPayload, normalize_text


def test_payload_and_normalization_flow() -> None:
    payload = MockPayload(text="  Mixed   CASE  ")
    assert normalize_text(payload.text) == "mixed case"
