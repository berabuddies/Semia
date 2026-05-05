.PHONY: help check compile test validate-plugin-manifests build release-check clean

UV ?= uv
PYTHON ?= python3
BUILD_DIR ?= dist

COMPILE_DIRS = tests $(wildcard packages)
TEST_DIRS = $(sort $(dir $(wildcard tests/test*.py) $(wildcard tests/*/test*.py) $(wildcard tests/*/*/test*.py)))
RELEASE_REQUIRED = README.md LICENSE docs/release.md docs/supply-chain.md

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-24s %s\n", $$1, $$2}'

# ── Quality Gates ────────────────────────────────────────────────────

check: compile test validate-plugin-manifests ## Run all local checks

compile: ## Byte-compile Python sources with stdlib compileall
	$(PYTHON) -m compileall -q $(COMPILE_DIRS)

test: ## Run stdlib unittest discovery
	@if [ -z "$(TEST_DIRS)" ]; then \
		echo "No tests found."; \
	else \
		for dir in $(TEST_DIRS); do \
			$(PYTHON) -m unittest discover -s $$dir || exit $$?; \
		done; \
	fi

validate-plugin-manifests: ## Validate plugin manifests with a stdlib checker
	$(PYTHON) .github/scripts/validate_plugin_manifests.py

# ── Packaging / Release ──────────────────────────────────────────────

build: ## Run package metadata and package-data checks
	$(PYTHON) .github/scripts/package_build_check.py --out $(BUILD_DIR)/build-check.json

release-check: check build ## Run release readiness checks
	$(PYTHON) -c "from pathlib import Path; import sys; missing=[p for p in '$(RELEASE_REQUIRED)'.split() if not Path(p).exists()]; sys.exit('Missing release files: '+', '.join(missing)) if missing else print('release files present')"

clean: ## Remove local build artifacts
	rm -rf $(BUILD_DIR) build *.egg-info
