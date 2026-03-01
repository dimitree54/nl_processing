import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--e2e-client",
        action="store",
        choices=("serverless", "serverfull"),
        default="serverless",
        help="Select e2e client backend.",
    )
