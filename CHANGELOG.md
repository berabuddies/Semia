# Changelog

All notable changes to Semia Skillscan are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `SECURITY.md` private vulnerability reporting policy and threat model.
- `CONTRIBUTING.md` with DCO sign-off requirement and local development
  workflow.
- `CHANGELOG.md` (this file).
- `NOTICE` attribution file required by Apache-2.0.
- `TRADEMARKS.md` describing the trademark policy for the Semia /
  Skillscan / RiemaLabs marks.
- Pre-commit configuration (`.pre-commit-config.yaml`) covering file
  hygiene, ruff lint/format, private-key detection, and gitleaks secret
  scanning.
- `.gitleaks.toml` with project-specific allowlists for example env files
  and test fixtures.
- GitHub Actions workflows: `lint.yml` (runs pre-commit) and
  `gitleaks.yml` (full-history secret scan, including a weekly schedule).
- `[tool.ruff]` configuration in `pyproject.toml`.
- `SPDX-License-Identifier: Apache-2.0` headers on every Python source
  file under `packages/`, `tests/`, `build_backend/`, and
  `.github/scripts/`.

### Changed
- **License switched from `CC-BY-NC-ND-4.0` to `Apache-2.0`.** Updates
  cover `LICENSE`, `pyproject.toml` (`license` SPDX expression and
  `license-files`, removed `License :: Other/Proprietary License`
  classifier), `README.md` license section, `build_backend/semia_build.py`
  metadata generator (now reads the license expression from
  `pyproject.toml` so version/license live in one place), and the three
  plugin manifests under `packages/semia-plugins/`.
- `.github/scripts/package_build_check.py` and
  `.github/scripts/validate_plugin_manifests.py` now enforce
  `Apache-2.0` (and PEP 639 SPDX `license` strings).

## [0.1.0] - 2026-05-04

### Added
- Initial release of Semia Skillscan.
- `semia-core` deterministic analysis library: prepare, structural checker,
  evidence alignment, Datalog detector, Markdown / SARIF report.
- `semia-cli` command surface: `semia scan`, `semia synthesize`,
  `semia detect`, `semia report`, plus prepare-only and offline-baseline
  modes.
- `semia-plugins` host integrations for Codex, Claude Code, and OpenClaw,
  with a shared `semia-audit` skill workflow.
- Souffle-backed Datalog detection with bundled SDL rules under
  `packages/semia-core/src/semia_core/rules/sdl/`.
- LLM provider adapters for OpenAI (default), Anthropic SDK, Codex CLI, and
  Claude Code, with a synthesis review loop, plateau detection, and
  incremental Datalog patch merging.
- CI workflows for `check`, `build`, and release readiness, plus
  `dependabot.yml` for GitHub Actions and Python dependency updates.
- Plugin-manifest validation and package metadata checks via stdlib-only
  scripts under `.github/scripts/`.

[Unreleased]: https://github.com/RiemaLabs/semia-skillscan/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/RiemaLabs/semia-skillscan/releases/tag/v0.1.0
