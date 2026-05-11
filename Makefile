.PHONY: help test compile validate-plugin-manifests check \
        build-check dist-build twine-check build \
        bundle-plugins bundle-codex-plugin \
        release-check clean

PYTHON ?= python3
BUILD_DIR ?= dist
PYTHONPATH := packages/semia-core/src:packages/semia-cli/src

# `dist-build` and `twine-check` need the standard PyPA tooling (build, twine).
# CI installs them via `uv pip install --system build twine`. Locally, run
# `python -m pip install build twine` once before `make build`.

PLUGIN_HOSTS = codex claude-code openclaw

RELEASE_REQUIRED = README.md LICENSE docs/release.md docs/supply-chain.md

help:
	@echo "Available targets:"
	@echo "  test                      - run unit tests"
	@echo "  compile                   - byte-compile sources"
	@echo "  validate-plugin-manifests - check plugin manifests"
	@echo "  check                     - compile + tests + manifest validation"
	@echo "  build-check               - validate package metadata (writes $(BUILD_DIR)/build-check.json)"
	@echo "  dist-build                - build wheel and sdist into $(BUILD_DIR)/"
	@echo "  twine-check               - validate built artifacts with twine"
	@echo "  build                     - build-check + dist-build + twine-check"
	@echo "  bundle-plugins            - rebuild semia.pyz for every host in PLUGIN_HOSTS"
	@echo "  bundle-plugin-<host>      - rebuild packages/semia-plugins/<host>/bin/semia.pyz"
	@echo "  bundle-codex-plugin       - alias for bundle-plugin-codex"
	@echo "  release-check             - check + build + verify required release files"
	@echo "  clean                     - remove build artifacts"

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest \
	    tests.cli.test_semia_cli \
	    tests.cli.test_semia_cli_integration \
	    tests.cli.test_llm_adapter \
	    tests.core.test_datalog_eval \
	    tests.core.test_detector_report \
	    tests.core.test_facts_checker_evidence \
	    tests.core.test_prepare

compile:
	$(PYTHON) -m compileall -q packages/ build_backend/

validate-plugin-manifests:
	$(PYTHON) .github/scripts/validate_plugin_manifests.py

check: compile test validate-plugin-manifests

build-check:
	$(PYTHON) .github/scripts/package_build_check.py --out $(BUILD_DIR)/build-check.json

dist-build:
	$(PYTHON) -m build --no-isolation --wheel --sdist --outdir $(BUILD_DIR)/ .

twine-check:
	$(PYTHON) -m twine check $(BUILD_DIR)/*.tar.gz $(BUILD_DIR)/*.whl

build: clean build-check dist-build twine-check

bundle-plugins: $(addprefix bundle-plugin-,$(PLUGIN_HOSTS))

bundle-plugin-%:
	@rm -rf $(BUILD_DIR)/.zipapp-stage
	@mkdir -p $(BUILD_DIR)/.zipapp-stage packages/semia-plugins/$*/bin
	@cp -r packages/semia-cli/src/semia_cli $(BUILD_DIR)/.zipapp-stage/
	@cp -r packages/semia-core/src/semia_core $(BUILD_DIR)/.zipapp-stage/
	@find $(BUILD_DIR)/.zipapp-stage -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	$(PYTHON) -m zipapp $(BUILD_DIR)/.zipapp-stage \
	    -m "semia_cli:main" \
	    -p "/usr/bin/env python3" \
	    -o packages/semia-plugins/$*/bin/semia.pyz
	@chmod +x packages/semia-plugins/$*/bin/semia.pyz
	@rm -rf $(BUILD_DIR)/.zipapp-stage
	@echo "built packages/semia-plugins/$*/bin/semia.pyz"

bundle-codex-plugin: bundle-plugin-codex

release-check: check build
	@$(PYTHON) -c "from pathlib import Path; import sys; missing=[p for p in '$(RELEASE_REQUIRED)'.split() if not Path(p).exists()]; sys.exit('Missing release files: '+', '.join(missing)) if missing else print('release files present')"

clean:
	rm -rf $(BUILD_DIR) build *.egg-info
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
