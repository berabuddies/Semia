# Development

## Repository layout

```text
packages/
  semia-core/       # deterministic analysis library (prepare, check, detect, report)
  semia-cli/        # `semia` command surface
  semia-plugins/    # Codex / Claude Code / OpenClaw integrations
docs/
  architecture.md
  plugin-protocol.md
  release.md
  supply-chain.md
tests/

```

## Development workflow

```bash
git clone https://github.com/berabuddies/Semia
cd semia
python3 -m venv --clear .venv
source .venv/bin/activate
python -m pip install -e .
python -m pip install pre-commit
pre-commit install
pre-commit run --all-files     # establish a clean baseline

make help            # list targets
make check           # compile + tests + manifest validation
make build           # package metadata check
make release-check   # full pre-release gate
```

The root quality gates stay stdlib-friendly: `compileall`, `unittest`
discovery, and stdlib-only validators. Pre-commit adds `ruff` lint/format
and `gitleaks` secret scanning. CI mirrors `ruff` via
[`lint.yml`](.github/workflows/lint.yml); `gitleaks` stays local-only
because the upstream GitHub Action now requires a paid license for
organization repositories.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow and the DCO
sign-off requirement.
