lint:
	uv run ruff format src tests
	uv run ruff check --fix src tests
	uv run pylint src tests --load-plugins=pylint.extensions.bad_builtin --disable=all --enable=C0302,W0141 --max-module-lines=200 --bad-functions=hasattr,getattr,setattr
	uv run vulture src tests vulture_whitelist.py
	@output=$$(npx jscpd --config .jscpd.json --exitCode 1 src tests 2>&1); rc=$$?; [ $$rc -eq 0 ] || { echo "$$output"; exit $$rc; }

test-unit:
	uv run pytest -n auto tests/unit

check: lint test-unit
