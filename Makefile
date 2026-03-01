check:
	uv run ruff format
	uv run ruff check --fix
	uvx pylint nl_processing tests --disable=all --enable=C0302 --max-module-lines=200
	uvx pylint nl_processing tests --load-plugins=pylint.extensions.bad_builtin --disable=all --enable=W0141 --bad-functions=hasattr,getattr,setattr
	uv run vulture nl_processing tests vulture_whitelist.py
	npx jscpd --exitCode 1
	uv run pytest -n auto tests/unit
	uv run pytest -n auto tests/integration
	uv run pytest -n auto tests/e2e --e2e-client=serverless
