import pytest


def test_e2e_option_is_available(request: pytest.FixtureRequest) -> None:
    backend: str = request.config.getoption("--e2e-client")
    assert backend == "serverless"
