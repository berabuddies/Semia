# Semia Skillscan

> **Static security audit for AI agent skills.** Know what a skill *can* do
> before you trust it.

[![CI](https://github.com/RiemaLabs/semia-skillscan/actions/workflows/ci.yml/badge.svg)](https://github.com/RiemaLabs/semia-skillscan/actions/workflows/ci.yml)
[![Lint](https://github.com/RiemaLabs/semia-skillscan/actions/workflows/lint.yml/badge.svg)](https://github.com/RiemaLabs/semia-skillscan/actions/workflows/lint.yml)
[![Gitleaks](https://github.com/RiemaLabs/semia-skillscan/actions/workflows/gitleaks.yml/badge.svg)](https://github.com/RiemaLabs/semia-skillscan/actions/workflows/gitleaks.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

Agent skills are markdown files with embedded shell commands, network calls,
and tool invocations. They run with **your credentials, on your machine,
with your data**. Skillscan reads a skill as data — never executes it — and
produces an evidence-backed report of every capability it may exercise.

It is the difference between

> *"I trust this skill because the README looks fine."*

and

> *"I trust this skill because Skillscan extracted 14 actions, 6 effects,
> and 2 secret reads — and every one is grounded in a specific source line."*

---

## Quick example

In your shell:

```bash
git clone https://github.com/RiemaLabs/semia-skillscan
cd semia-skillscan && pip install -e .
semia scan ./some-skill --out .semia/runs/some-skill
```

Or inside Codex, Claude Code, or OpenClaw, just ask:

> Run Semia audit on this skill

You get a Markdown report and a [SARIF 2.1.0](https://sarifweb.azurewebsites.net/)
file: findings ranked by severity, every finding tied to specific source
lines, and a Datalog program you can re-query.

## What you get

A run writes the following under `.semia/runs/<run-id>/`:

| Artifact                  | Purpose                                            |
| ------------------------- | -------------------------------------------------- |
| `report.md`               | human-readable findings with evidence              |
| `report.sarif.json`       | SARIF 2.1.0 — drop into GitHub Code Scanning       |
| `synthesized_facts.dl`    | the behavior map (Datalog facts)                   |
| `detection_findings.dl`   | findings derived by rule evaluation                |
| `prepared_skill.md`       | normalized skill text with stable line anchors     |
| `prepare_units.json`      | reference units the evidence text aligns against   |
| `synthesis_metadata.json` | provider, model, retries, score, stop reason       |
| `run_manifest.json`       | end-to-end manifest of the run                     |

Because every finding traces back to a source line, the SARIF drops cleanly
into GitHub Code Scanning and reviewers see annotations directly on the
skill PR.

## How it works

```text
   ┌──────────┐     ┌────────────┐     ┌──────────┐     ┌────────┐
   │ Prepare  │ ──▶ │ Synthesize │ ──▶ │  Detect  │ ──▶ │ Report │
   │  (det.)  │     │   (LLM)    │     │  (det.)  │     │ (det.) │
   └──────────┘     └────────────┘     └──────────┘     └────────┘
```

1. **Prepare** — read skill markdown + adjacent source, inline references,
   assign stable evidence handles. Pure stdlib. No LLM.
2. **Synthesize** — an LLM (or the host agent's own session) extracts a
   *behavior map* as Datalog facts (`action`, `call`, `call_effect`, …)
   with `_evidence_text` sidecars citing the original source. The loop
   retries invalid candidates with checker feedback and keeps the best one.
3. **Detect** — a Datalog evaluator runs the bundled SDL rules over the
   facts to flag risky combinations (e.g. *secret read → network write*).
4. **Report** — render Markdown for humans and SARIF for CI.

Detection runs through a built-in pure-Python Datalog evaluator by default,
so **no external binary is required**. If [Soufflé](https://souffle-lang.github.io/)
is on `PATH` (or `SEMIA_SOUFFLE_BIN`) it is preferred as a faster backend.
Override with `SEMIA_DETECTOR_BACKEND=auto|souffle|builtin`.

[Read the full architecture →](docs/architecture.md)

## Trust model

Skillscan is a security tool for analyzing untrusted content. The trust
boundary is explicit:

| Surface                   | Treatment                                                                        |
| ------------------------- | -------------------------------------------------------------------------------- |
| Audited skill             | **untrusted data** — never executed, hooks/installers ignored                    |
| Skill-declared URLs       | **never fetched** during a scan                                                  |
| Prompt-injection in skill | **recorded as evidence**, not followed as instructions                           |
| Prepare / Detect / Report | deterministic, stdlib-friendly, runs locally                                     |
| Synthesize                | the only LLM-mediated step; output must pass structural and evidence checks      |
| Network                   | LLM provider only                                                                |
| Filesystem                | reads the skill directory; writes only `.semia/runs/<run-id>/`                   |

See [docs/plugin-protocol.md#hostile-input-rules](docs/plugin-protocol.md)
for the full host-integration contract, and
[SECURITY.md](SECURITY.md) for vulnerability reporting.

## Install

From source (current):

```bash
git clone https://github.com/RiemaLabs/semia-skillscan
cd semia-skillscan
python3 -m venv --clear .venv
source .venv/bin/activate
python -m pip install -e .
```

For direct Anthropic SDK synthesis, install the optional extra:

```bash
python -m pip install -e ".[anthropic]"
```

Python 3.11+ required. The root project has zero runtime dependencies.

## Configuration

Settings come from CLI flags, environment variables, or a repo-local
`.env`. Copy [`.env.example`](.env.example) to `.env` and fill in your
credentials — `.env` is gitignored, and CI runs `gitleaks` to make sure
nothing leaks into the history.

### Providers

The default provider is `openai` with model `gpt-5.5`, authenticated via
`OPENAI_API_KEY`.

| Provider    | How to reach it                       | Auth                                                  |
| ----------- | ------------------------------------- | ----------------------------------------------------- |
| `openai`    | streams the Responses API             | `OPENAI_API_KEY`, optional `OPENAI_BASE_URL`          |
| `anthropic` | Python Anthropic SDK (extra required) | `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN`         |
| `claude`    | shells out to Claude Code             | inherits Claude Code env (`ANTHROPIC_*`)              |
| `codex`     | shells out to Codex CLI               | inherits Codex CLI config                             |

Switch with a flag:

```bash
semia scan ./some-skill --out .semia/runs/some-skill --provider anthropic
semia scan ./some-skill --out .semia/runs/some-skill --provider claude --model claude-sonnet-4-5
```

### Most common environment variables

| Variable                    | Purpose                                                       |
| --------------------------- | ------------------------------------------------------------- |
| `SEMIA_LLM_PROVIDER`        | `openai` (default), `anthropic`, `claude`, `codex`            |
| `SEMIA_LLM_MODEL`           | model name passed to the provider                             |
| `SEMIA_LLM_TIMEOUT`         | request timeout in seconds                                    |
| `SEMIA_LLM_MAX_RETRIES`     | retry budget                                                  |
| `SEMIA_DETECTOR_BACKEND`    | `auto` (default), `souffle`, `builtin`                        |
| `SEMIA_SOUFFLE_BIN`         | path to `souffle` if not on `PATH`                            |

For full synthesis tuning (`SEMIA_SYNTHESIS_*`), see the rest of
[`.env.example`](.env.example) and
[docs/plugin-protocol.md](docs/plugin-protocol.md).

## Common workflows

**Stop after deterministic preparation:**
```bash
semia scan ./some-skill --out .semia/runs/some-skill --prepare-only
```

**Reuse facts from a prior run or an agent session:**
```bash
semia scan ./some-skill --out .semia/runs/some-skill --facts synthesized_facts.dl
semia report .semia/runs/some-skill --format sarif
```

**CI smoke test (no LLM call):**
```bash
semia scan ./some-skill --out .semia/runs/some-skill --offline-baseline
```
> `--offline-baseline` is a conservative non-LLM fallback for offline demos
> and CI smoke tests. It is **not** a substitute for real synthesis.

## Install as a host plugin

Each plugin bundle under `packages/semia-plugins/<host>/` ships with a
self-contained `bin/semia.pyz` zipapp, so the plugin works out of the box
without a separate `pip install semia-skillscan`. Installing the Python
package as well is recommended if you want `semia` available as a normal
shell command alongside the in-host workflow.

**Codex** — add the marketplace and install the plugin:

```bash
codex marketplace add RiemaLabs/semia-skillscan
codex plugin install semia-audit
```

**Claude Code** — add the marketplace from inside Claude Code and install:

```text
/plugin marketplace add RiemaLabs/semia-skillscan
/plugin install semia-audit@semia-skillscan
```

See [Discover and install plugins](https://docs.claude.com/en/docs/claude-code/plugins)
for the full plugin manager UX.

**OpenClaw** — copy the plugin directory into your OpenClaw plugins root:

```bash
cp -r packages/semia-plugins/openclaw ~/.openclaw/plugins/semia-audit
```

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

## Development

```bash
git clone https://github.com/RiemaLabs/semia-skillscan
cd semia-skillscan
python3 -m venv --clear .venv
source .venv/bin/activate
python -m pip install -e ".[anthropic]"
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
and `gitleaks` secret scanning; CI mirrors both via
[`lint.yml`](.github/workflows/lint.yml) and
[`gitleaks.yml`](.github/workflows/gitleaks.yml).

See [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow and the DCO
sign-off requirement.

## Project background

The technique behind Semia Skillscan is described in the Semia paper
([Semia paper, in preparation](https://github.com/RiemaLabs/semia-skillscan)). Skillscan is the
**deterministic acceptance boundary** around behavior mapping: agents may
extract facts, but only checked, evidence-grounded facts make it into a
report.

## Security

To report a security vulnerability, see [SECURITY.md](SECURITY.md). Please
do **not** file public GitHub issues for security problems.

## Contributing

Contributions are welcome — bug reports, documentation fixes, detector
rules, and code. See [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow
and the DCO sign-off requirement.

## License & trademarks

Semia Skillscan is released under the [Apache License 2.0](LICENSE). You
may use, modify, and redistribute it freely, including for commercial
purposes, subject to the terms of the license. See [NOTICE](NOTICE) for
attribution.

The names **"Semia"**, **"Skillscan"**, **"Semia Skillscan"**, and
**"RiemaLabs"** are trademarks of RiemaLabs and are **not** licensed under
Apache-2.0. See [TRADEMARKS.md](TRADEMARKS.md) for the trademark policy.
