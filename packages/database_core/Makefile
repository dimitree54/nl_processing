PACKAGE_PYTHONPATH := src:../core/src:../database/src
PYLINT := env PYTHONPATH="$(PACKAGE_PYTHONPATH)" uv run pylint
PYTEST := env PYTHONPATH="$(PACKAGE_PYTHONPATH)" uv run pytest
VULTURE := env PYTHONPATH="$(PACKAGE_PYTHONPATH)" uv run vulture
JCSPD := npx jscpd --config .jscpd.json --exitCode 1
INTEGRATION_ROOT := tests/integration/database_core
LIFECYCLE_TEST := $(INTEGRATION_ROOT)/test_table_creation.py

.PHONY: lint test-unit test-integration check

lint:
	uv sync --group dev
	uv run ruff format src tests
	uv run ruff check --fix src tests
	$(PYLINT) src tests --disable=all --enable=C0302 --max-module-lines=200
	$(PYLINT) src tests --load-plugins=pylint.extensions.bad_builtin --disable=all --enable=W0141 --bad-functions=hasattr,getattr,setattr
	$(VULTURE) src tests vulture_whitelist.py
	$(JCSPD) src tests

test-unit:
	uv sync --group dev
	$(PYTEST) -n auto tests/unit

test-integration:
	uv sync --group dev
	doppler run -- env PYTHONPATH="$(PACKAGE_PYTHONPATH)" uv run pytest "$(INTEGRATION_ROOT)" --ignore="$(LIFECYCLE_TEST)"
	doppler run -- env PYTHONPATH="$(PACKAGE_PYTHONPATH)" uv run pytest "$(LIFECYCLE_TEST)"

check: lint test-unit test-integration
