PACKAGE_PYTHONPATH := src:../core/src:../database/src:../database_cache/src
PYLINT := env PYTHONPATH="$(PACKAGE_PYTHONPATH)" uv run pylint
PYTEST := env PYTHONPATH="$(PACKAGE_PYTHONPATH)" uv run pytest
VULTURE := env PYTHONPATH="$(PACKAGE_PYTHONPATH)" uv run vulture
JCSPD := npx jscpd --config .jscpd.json --exitCode 1

.PHONY: lint test test-unit test-integration test-e2e check

lint:
	uv run ruff format src tests
	uv run ruff check --fix src tests
	$(PYLINT) src tests --disable=all --enable=C0302 --max-module-lines=200
	$(PYLINT) src tests --load-plugins=pylint.extensions.bad_builtin --disable=all --enable=W0141 --bad-functions=hasattr,getattr,setattr
	$(VULTURE) src tests vulture_whitelist.py
	$(JCSPD) src tests

test: test-unit test-integration test-e2e

test-unit:
	$(PYTEST) -n auto tests/unit

test-integration:
	@if [ -d tests/integration ]; then \
		doppler run -- env PYTHONPATH="$(PACKAGE_PYTHONPATH)" uv run pytest -n auto tests/integration; \
	fi

test-e2e:
	@if [ -d tests/e2e ]; then \
		doppler run -- env PYTHONPATH="$(PACKAGE_PYTHONPATH)" uv run pytest -n auto tests/e2e; \
	fi

check: lint test
