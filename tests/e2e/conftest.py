import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register --e2e-client option for backward compatibility with Makefile."""
    parser.addoption("--e2e-client", default="serverless")
