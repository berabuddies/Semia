.PHONY: help test coverage compile validate-plugin-manifests check types \
        build-check dist-build twine-check check-sdist build \
        bundle-plugins bundle-codex-plugin \
        assemble-plugin-skills check-plugin-skills \
        smoke-installed smoke-zipapps \
        release-check clean

PYTHON ?= python3
BUILD_DIR ?= dist
PYTHONPATH := packages/semia-core/src:packages/semia-cli/src
COVERAGE_SOURCES := packages/semia-core/src,packages/semia-cli/src

# `dist-build` and `twine-check` need the standard PyPA tooling (build, twine).
# CI installs them via `uv pip install --system build twine`. Locally, run
# `python -m pip install build twine` once before `make build`.

PLUGIN_HOSTS = codex claude-code

help:
	@echo "Available targets:"
	@echo "  test                      - run unit tests"
	@echo "  coverage                  - run unit tests under coverage.py (writes coverage.xml)"
	@echo "  compile                   - byte-compile sources"
	@echo "  validate-plugin-manifests - check plugin manifests"
	@echo "  types                     - run mypy over packages/ and build_backend/"
	@echo "  check                     - compile + tests + manifest validation"
	@echo "  build-check               - validate package metadata (writes $(BUILD_DIR)/build-check.json)"
	@echo "  dist-build                - build wheel and sdist into $(BUILD_DIR)/"
	@echo "  twine-check               - validate built artifacts with twine"
	@echo "  check-sdist               - assert sdist does not leak dev state (tests/, .coverage, ...)"
	@echo "  build                     - build-check + dist-build + twine-check + check-sdist"
	@echo "  bundle-plugins            - rebuild semia.pyz for every host in PLUGIN_HOSTS"
	@echo "  bundle-plugin-<host>      - rebuild packages/semia-plugins/<host>/bin/semia.pyz"
	@echo "  bundle-codex-plugin       - alias for bundle-plugin-codex"
	@echo "  assemble-plugin-skills    - rebuild per-host SKILL.md from shared body + overlays"
	@echo "  check-plugin-skills       - verify committed SKILL.md files match the assembled output"
	@echo "  smoke-installed           - install the built wheel and run 'semia --help'"
	@echo "  smoke-zipapps             - run 'python <host>/bin/semia.pyz --help' for each host"
	@echo "  release-check             - check + build + verify required release files"
	@echo "  clean                     - remove build artifacts"

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest \
	    tests.cli.test_semia_cli \
	    tests.cli.test_semia_cli_integration \
	    tests.cli.test_llm_adapter \
	    tests.cli.test_repair \
	    tests.core.test_datalog_eval \
	    tests.core.test_detector_report \
	    tests.core.test_facts_checker_evidence \
	    tests.core.test_pipeline \
	    tests.core.test_prepare \
	    tests.core.test_repair \
	    tests.core.test_skill_corpus

coverage:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m coverage run --source=$(COVERAGE_SOURCES) -m unittest \
	    tests.cli.test_semia_cli \
	    tests.cli.test_semia_cli_integration \
	    tests.cli.test_llm_adapter \
	    tests.cli.test_repair \
	    tests.core.test_datalog_eval \
	    tests.core.test_detector_report \
	    tests.core.test_facts_checker_evidence \
	    tests.core.test_pipeline \
	    tests.core.test_prepare \
	    tests.core.test_repair \
	    tests.core.test_skill_corpus
	$(PYTHON) -m coverage xml -o coverage.xml
	$(PYTHON) -m coverage report

compile:
	$(PYTHON) -m compileall -q packages/ build_backend/

validate-plugin-manifests:
	$(PYTHON) .github/scripts/validate_plugin_manifests.py

assemble-plugin-skills:
	$(PYTHON) .github/scripts/assemble_plugin_skills.py

check-plugin-skills:
	$(PYTHON) .github/scripts/assemble_plugin_skills.py --check

check: compile test validate-plugin-manifests check-plugin-skills

# Run mypy in permissive mode (`ignore_missing_imports`, no `disallow_untyped_defs`
# yet). The CI step that calls this target is `continue-on-error: true` for now
# so existing code lands as a baseline; tighten the config as type coverage grows.
types:
	$(PYTHON) -m mypy --config-file pyproject.toml \
	    packages/semia-core/src \
	    packages/semia-cli/src \
	    build_backend

build-check:
	$(PYTHON) .github/scripts/package_build_check.py --out $(BUILD_DIR)/build-check.json

dist-build:
	$(PYTHON) -m build --no-isolation --wheel --sdist --outdir $(BUILD_DIR)/ .

twine-check:
	$(PYTHON) -m twine check $(BUILD_DIR)/*.tar.gz $(BUILD_DIR)/*.whl

# Regression guard: assert the sdist tarball only contains allowlisted files.
# Catches any future change to build_backend/semia_build.py that accidentally
# starts shipping tests/, .coverage, .agents/, etc.
check-sdist:
	$(PYTHON) .github/scripts/check_sdist_contents.py $(BUILD_DIR)/*.tar.gz

build: clean build-check dist-build twine-check check-sdist

bundle-plugins: $(addprefix bundle-plugin-,$(PLUGIN_HOSTS))

bundle-plugin-%:
	@rm -rf $(BUILD_DIR)/.zipapp-stage
	@mkdir -p $(BUILD_DIR)/.zipapp-stage packages/semia-plugins/$*/bin
	@cp -r packages/semia-cli/src/semia_cli $(BUILD_DIR)/.zipapp-stage/
	@cp -r packages/semia-core/src/semia_core $(BUILD_DIR)/.zipapp-stage/
	@find $(BUILD_DIR)/.zipapp-stage -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	# Do NOT pass --python here. On Windows runners CI uses Git Bash, and
	# MSYS auto-converts argv entries that look like POSIX paths
	# (`/usr/bin/env python3` -> `C:/Program Files/Git/usr/bin/env python3`),
	# which would silently change the shebang baked into the zipapp and
	# break the CI drift check. The script's own default
	# (`/usr/bin/env python3`, set in Python source) is identical and
	# beyond MSYS reach.
	$(PYTHON) .github/scripts/build_zipapp.py \
	    --source $(BUILD_DIR)/.zipapp-stage \
	    --main "semia_cli:main" \
	    --out packages/semia-plugins/$*/bin/semia.pyz
	@rm -rf $(BUILD_DIR)/.zipapp-stage

bundle-codex-plugin: bundle-plugin-codex

# Install the freshly built wheel into the active environment and confirm the
# `semia` console entry point is wired up. Catches packaging bugs (missing
# package data, wrong entry point string) that `twine check` cannot detect.
smoke-installed:
	$(PYTHON) -m pip install --force-reinstall --no-deps $(BUILD_DIR)/*.whl
	semia --help > /dev/null
	@echo "smoke-installed: semia entry point is importable"

# Confirm each bundled zipapp actually runs end-to-end (the drift check in CI
# only verifies bytes match; this verifies the bundle is functionally intact).
smoke-zipapps:
	@for host in $(PLUGIN_HOSTS); do \
	    echo "smoke: $$host" ; \
	    $(PYTHON) "packages/semia-plugins/$$host/bin/semia.pyz" --help > /dev/null ; \
	done

release-check: check build
	$(PYTHON) .github/scripts/check_release_files.py

clean:
	rm -rf $(BUILD_DIR) build *.egg-info
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
