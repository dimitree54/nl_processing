ROOT_DIR := $(abspath ../..)
TOOLS_VENV ?= $(shell if [ -x "$(CURDIR)/.venv/bin/pytest" ] && [ -x "$(CURDIR)/.venv/bin/ruff" ] && [ -x "$(CURDIR)/.venv/bin/pylint" ] && [ -x "$(CURDIR)/.venv/bin/vulture" ]; then printf '%s' "$(CURDIR)/.venv"; else printf '%s' "$(ROOT_DIR)/.venv"; fi)

.PHONY: check

check:
	$(MAKE) -C "$(ROOT_DIR)" package-check PKG=database_cache PACKAGE_PYTHONPATH=src:../core/src:../database/src:../translate_word/src TOOLS_VENV="$(TOOLS_VENV)"
