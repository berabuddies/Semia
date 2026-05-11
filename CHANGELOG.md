# Changelog

All notable changes to Semia are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-05-11

Initial public release. Semia ships a deterministic Skill Behavior
Mapping pipeline, an LLM-mediated synthesis step with a review loop, host
plugins for Codex / Claude Code / OpenClaw, and an automated PyPI + ClawHub
release pipeline.

### Core analysis (`semia-core`)

- Deterministic prepare → check → detect → report pipeline with a single
  artifact contract (`semia-run-v1`) per run directory.
- Structural checker with SSA input-availability metric and an
  evidence-taint threshold gate that flags facts citing text not present
  in `prepared_skill.md` (likely hallucination or prompt-injection echo).
- Evidence alignment from synthesized facts to prepared reference units.
- Datalog detector with bundled SDL rules under
  `packages/semia-core/src/semia_core/rules/sdl/`.
- Soufflé-backed evaluation when available, with a pure-Python built-in
  evaluator as the default fallback. Selectable via
  `SEMIA_DETECTOR_BACKEND=auto|souffle|builtin` (or pinned with
  `SEMIA_SOUFFLE_BIN`).
- Markdown and SARIF 2.1.0 report renderers; SARIF drops cleanly into
  GitHub Code Scanning.
- `prepare_units.dl` artifact per run: Datalog facts describing prepared
  evidence units (handle ↔ id, type, source location) for downstream
  Soufflé queries.

### CLI (`semia-cli`)

- `semia scan`, `semia synthesize`, `semia detect`, `semia report`, plus
  prepare-only and offline-baseline modes.
- `--provider`, `--model`, `--base-url`, `--out` flags. `--base-url` is
  ignored with a stderr warning when used with `codex` / `claude`.

### LLM providers and synthesis loop

- Four providers — `responses` (default, OpenAI Responses API; `openai`
  accepted as alias), `anthropic`, `codex`, `claude` — with free-form
  model names. Default models: `gpt-5.5` for `responses`,
  `claude-opus-4-7` for `anthropic` / `claude`. CLI providers (`codex` /
  `claude`) only honor `--model`.
- `OPENAI_BASE_URL` / `ANTHROPIC_BASE_URL` env vars route HTTP providers
  at compatible endpoints (DeepSeek, OpenRouter, vLLM, local proxies).
- Anthropic Messages provider uses raw `urllib` HTTP streaming with no
  third-party SDK dependency — `pip install semia` is enough.
- `LlmSynthesisConfigError` non-retryable exception so missing API keys
  or binaries surface immediately instead of consuming the retry budget.
- Review loop with plateau detection and incremental Datalog patch
  merging.
- Composite score ceiling (default `0.9`) and weighted mean
  (`0.5·match + 0.3·support + 0.2·reference`) reported in
  `synthesis_metadata.json` and tunable via `SEMIA_SYNTHESIS_CEILING` and
  `SEMIA_SYNTHESIS_SCORE_WEIGHTS`.
- `SEMIA_OPENAI_TEMPERATURE` env knob for the `responses` provider
  (default `0`; empty string omits the field for reasoning models that
  reject `temperature`).
- Per-iteration unmatched-directive detection: hallucinated
  `// REPLACE:` / `// REMOVE:` targets mark the candidate invalid and
  feed back to the LLM rather than being silently dropped.
- `extract_facts` prefers fenced blocks tagged with a recognized fact
  language (`datalog` / `souffle` / `prolog` / `text` / `dl` / `facts` /
  `sdl`); falls back to blocks containing period-terminated lines;
  strips single-word tag lines so a stray ` ```bash ` fence cannot
  poison the candidate.
- Codex provider writes its scratch output
  (`.semia_codex_synthesis.txt`) inside a `try/finally` so a later run
  cannot return a previous call's output.

### Hostile-input handling

- `<<<SEMIA_HOSTILE_INPUT id=…>>>` … `<<<SEMIA_END id=…>>>` fence wraps
  prepared skill text, prior-iteration facts, and validation
  retry-feedback in synthesis prompts — attacker-derived strings echoed
  by the structural checker cannot escape into the next prompt.

### Host plugin integrations (`semia-plugins`)

- Codex plugin with marketplace manifest at
  [.agents/plugins/marketplace.json](.agents/plugins/marketplace.json);
  installs via `codex plugin marketplace add RiemaLabs/Semia`.
- Claude Code plugin with `.claude-plugin/plugin.json`; installs via
  `/plugin marketplace add RiemaLabs/Semia`.
- OpenClaw skill published as `semia` on ClawHub; declares
  `requires.bins: [semia]` and `install: [{kind: uv, package:
  semia}]` so ClawHub provisions the CLI on first use. End
  users install via `openclaw plugins install clawhub:semia`.
- Shared canonical workflow at
  `packages/semia-plugins/shared/skills/semia/SKILL.md`;
  per-host SKILL.md generated from shared body + overlays via
  `make assemble-plugin-skills`, verified in CI via
  `make check-plugin-skills`.
- Self-contained `bin/semia.pyz` zipapp bundled with each code-plugin
  host (Codex, Claude Code), rebuilt by `make bundle-plugins` and
  diff-checked against committed copies in the release workflow.

### CI, release, and governance

- GitHub Actions: `ci.yml`, `lint.yml`, `gitleaks.yml`, `codeql.yml`,
  `release.yml`. The release workflow is tag-driven (`v*` push) and
  publishes to PyPI via OIDC trusted publishing (no long-lived token)
  and to ClawHub via the `CLAWHUB_TOKEN` secret, gated on the `pypi`
  and `clawhub` GitHub environments respectively.
- Plugin-manifest and assembled-skill validation scripts under
  `.github/scripts/` (stdlib-only).
- Pre-commit (`.pre-commit-config.yaml`) covering file hygiene, ruff
  lint/format, private-key detection, and gitleaks secret scanning.
- `.gitleaks.toml` with project-specific allowlists for example env
  files and test fixtures.
- `SECURITY.md` (private vulnerability reporting policy + threat
  model), `CONTRIBUTING.md` (DCO sign-off + local development
  workflow), `NOTICE`, `TRADEMARKS.md`.
- `[tool.ruff]` configuration in `pyproject.toml`.
- `SPDX-License-Identifier: Apache-2.0` headers on every Python source
  file under `packages/`, `tests/`, `build_backend/`, and
  `.github/scripts/`.

### Licensing

- Licensed under Apache-2.0. `LICENSE`, `pyproject.toml` SPDX
  expression with `license-files`, and every plugin manifest declare
  `Apache-2.0`. `package_build_check.py` and
  `validate_plugin_manifests.py` enforce it.

[0.1.0]: https://github.com/RiemaLabs/Semia/releases/tag/v0.1.0
