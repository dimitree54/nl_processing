ROOT_DIR := $(abspath ../..)
TOOLS_VENV ?= $(shell if [ -x "$(CURDIR)/.venv/bin/pytest" ] && [ -x "$(CURDIR)/.venv/bin/ruff" ] && [ -x "$(CURDIR)/.venv/bin/pylint" ] && [ -x "$(CURDIR)/.venv/bin/vulture" ] && env PYTHONPATH="src:../core/src:../database/src:../translate_word/src" "$(CURDIR)/.venv/bin/python" -c "from nl_processing.core.models import Language" 2>/dev/null; then printf '%s' "$(CURDIR)/.venv"; else printf '%s' "$(ROOT_DIR)/.venv"; fi)

.PHONY: check

check:
	$(MAKE) -C "$(ROOT_DIR)" package-check PKG=extract_word_details PACKAGE_PYTHONPATH=src:../core/src:../database/src:../translate_word/src TOOLS_VENV="$(TOOLS_VENV)"