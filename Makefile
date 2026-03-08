PACKAGES = core extract_text_from_image extract_words_from_text translate_text translate_word database database_cache sampling

ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
TOOLS_VENV ?= $(ROOT_DIR)/.venv
RUFF := $(TOOLS_VENV)/bin/ruff
PYLINT := $(TOOLS_VENV)/bin/pylint
PYTEST := $(TOOLS_VENV)/bin/pytest
VULTURE := $(TOOLS_VENV)/bin/vulture
JCSPD := npx jscpd --config $(ROOT_DIR)/.jscpd.json --exitCode 1

.PHONY: check package-check

check:
	"$(VULTURE)" packages/*/src packages/*/tests "$(ROOT_DIR)/vulture_whitelist.py"
	$(JCSPD) packages
	set -e; \
	for pkg in $(PACKAGES); do \
		$(MAKE) -C "$(ROOT_DIR)/packages/$$pkg" check; \
	done

package-check:
	@if [ -z "$(PKG)" ]; then \
		echo "PKG is required"; \
		exit 1; \
	fi
	@if [ -z "$(PACKAGE_PYTHONPATH)" ]; then \
		echo "PACKAGE_PYTHONPATH is required"; \
		exit 1; \
	fi
	cd "$(ROOT_DIR)/packages/$(PKG)" && \
		"$(RUFF)" format src tests && \
		"$(RUFF)" check --fix src tests && \
		"$(PYLINT)" src tests --disable=all --enable=C0302 --max-module-lines=200 && \
		"$(PYLINT)" src tests --load-plugins=pylint.extensions.bad_builtin --disable=all --enable=W0141 --bad-functions=hasattr,getattr,setattr && \
		env PYTHONPATH="$(PACKAGE_PYTHONPATH)" "$(PYTEST)" -n auto tests/unit
	@if [ -d "$(ROOT_DIR)/packages/$(PKG)/tests/integration" ]; then \
		cd "$(ROOT_DIR)/packages/$(PKG)" && \
		doppler run -- env PYTHONPATH="$(PACKAGE_PYTHONPATH)" "$(PYTEST)" -n auto tests/integration; \
	fi
	@if [ -d "$(ROOT_DIR)/packages/$(PKG)/tests/e2e" ]; then \
		cd "$(ROOT_DIR)/packages/$(PKG)" && \
		doppler run -- env PYTHONPATH="$(PACKAGE_PYTHONPATH)" "$(PYTEST)" -n auto tests/e2e; \
	fi
