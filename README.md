# Semia

> **Security audit for AI agent skills.** Know what a skill *can* do
> before you trust it.

[![CI](https://github.com/berabuddies/Semia/actions/workflows/ci.yml/badge.svg)](https://github.com/berabuddies/Semia/actions/workflows/ci.yml)
[![Lint](https://github.com/berabuddies/Semia/actions/workflows/lint.yml/badge.svg)](https://github.com/berabuddies/Semia/actions/workflows/lint.yml)
[![codecov](https://codecov.io/gh/berabuddies/Semia/graph/badge.svg)](https://codecov.io/gh/berabuddies/Semia)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

Agent skills are markdown files with embedded shell commands, network calls,
and tool invocations. They run with **your credentials, on your machine,
with your data**. Semia reads a skill as data — never executes it — and
produces an evidence-backed report of every capability it may exercise.

It is the difference between

> *"I trust this skill because the README looks fine."*

and

> *"I trust this skill because Semia extracted 14 actions, 6 effects,
> and 2 secret reads — and every one is grounded in a specific source line."*

---

## Quick example

Pick whichever fits how you already work.

### As a CLI

```bash
pip install semia
semia scan ./some-skill --out .semia/runs/some-skill
```

`scan` does prepare → synthesize (via your configured LLM provider) →
detect → report in one shot. You'll need an LLM provider configured first —
see [Set up an LLM provider](#set-up-an-llm-provider) below.

### Inside Codex, Claude Code, or OpenClaw

Install the plugin once. Each host has its own flow.

**Codex** — pick either path:

*Shell (one-liner):*

```bash
codex plugin marketplace add berabuddies/Semia
```

*Interactive plugin manager inside the Codex CLI:*

1. Launch `codex`.
2. Inside Codex, input `/plugins` (plural — opens the plugin panel).
3. Press **←** (Left) to enter **Add marketplace**.
4. Enter `berabuddies/Semia`.

Either path leaves the marketplace registered; install `semia`
from the panel or by re-running the relevant install command.

**Claude Code** — pick either path:

*Shell (one-liner):*

```bash
claude plugin marketplace add berabuddies/Semia
```

*Interactive plugin manager inside the Claude Code CLI:*

1. Launch `claude`.
2. Inside Claude Code, input `/plugins` (plural — opens the plugin panel).
3. Press **→** (Right) twice and select **Add Marketplace**.
4. Enter `berabuddies/Semia`.

Either path registers the marketplace; finish installing `semia` from
the panel or with `claude plugin install semia@semia`.

**OpenClaw** — one shell command registers the marketplace and installs:

```bash
openclaw plugins install clawhub:semia
```

Then in any chat with the host agent just ask:

> Run Semia audit on ./some-skill

The host agent itself acts as the synthesize step — **no API key needed**.
The bundled `semia.pyz` handles prepare / detect / report deterministically.

### Outputs

You get `report.md` — findings ranked by severity, every one tied to a
specific source line. Need [SARIF 2.1.0](https://sarifweb.azurewebsites.net/)
for GitHub Code Scanning, or structured JSON for downstream tooling? One
more command:

```bash
semia report .semia/runs/some-skill --format sarif    # for GitHub Code Scanning
semia report .semia/runs/some-skill --format json     # structured payload
```

## Set up an LLM provider

`semia scan` needs an LLM for the **synthesize** step (the other three
stages are deterministic, no key required). If you run Semia via a host
plugin (Codex / Claude Code / OpenClaw) skip this — the host agent already
does synthesize for you.

Four providers are supported. Pick one and export its credentials:

```bash
# OpenAI Responses API — default; also works for DeepSeek / OpenRouter / vLLM
export OPENAI_API_KEY=sk-...
# optional: export OPENAI_BASE_URL=https://api.deepseek.com/v1

# Anthropic Messages API
export SEMIA_LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-...
# optional: export ANTHROPIC_BASE_URL=https://api.anthropic.com

# Locally-installed Claude Code CLI (uses your Claude Code login)
export SEMIA_LLM_PROVIDER=claude

# Locally-installed Codex CLI (uses your Codex login)
export SEMIA_LLM_PROVIDER=codex
```

Override the model with `--model <name>` on any `semia scan` invocation, or
persist it via `SEMIA_LLM_MODEL`. Models are free-form strings — anything
the endpoint accepts (`gpt-5.5`, `deepseek-v4`, `claude-opus-4-7`, …).

See [Configuration](#configuration) for the full provider matrix, base-URL
support, timeout/retry knobs, and synthesis-loop tuning.

## What you get

A run writes everything under `.semia/runs/<run-id>/`. **Most users only
ever open the reports**:

| Report              | When                                                      |
| ------------------- | --------------------------------------------------------- |
| `report.md`         | always produced by `semia scan` — read this first         |
| `report.sarif.json` | on demand via `semia report --format sarif` — feed to GitHub Code Scanning |
| `report.json`       | on demand via `semia report --format json` — structured payload (check + evidence + detector) for programmatic consumers |

Because every finding traces back to a source line, the SARIF drops cleanly
into GitHub Code Scanning and reviewers see annotations directly on the
skill PR.

<details>
<summary>Other artifacts in the run directory (internal — for tooling, debugging, or re-querying)</summary>

| Artifact                  | Purpose                                            |
| ------------------------- | -------------------------------------------------- |
| `synthesized_facts.dl`    | the behavior map (Datalog facts) — re-queryable    |
| `detection_findings.dl`   | findings derived by rule evaluation                |
| `prepared_skill.md`       | normalized skill text with stable line anchors     |
| `prepare_units.json`      | reference units the evidence text aligns against   |
| `synthesis_metadata.json` | provider, model, retries, score, stop reason       |
| `run_manifest.json`       | end-to-end manifest of the run                     |

</details>

## Worked example

Picture a skill that promises to "summarize your inbox every day". It
installs a browser automation tool, opens your real Chrome (with every
saved login), reads Gmail, pipes the messages to an LLM that controls
the browser, and sets up a launchd job to repeat daily — forever. One
email from an attacker turns that skill into a remote control for every
site you are logged into.

[See **EXAMPLE.md** for the full walkthrough →](EXAMPLE.md) — the skill
source, the attack, why it works, and the exact capabilities Semia
surfaces before you install.

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

Semia is a security tool for analyzing untrusted content. The trust
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
git clone https://github.com/berabuddies/Semia
cd semia
python3 -m venv --clear .venv
source .venv/bin/activate
python -m pip install -e .
```

Python 3.11+ required. The project has **zero runtime dependencies** — both
the `responses` and `anthropic` providers talk to their APIs over raw HTTP
using the standard library.

## Configuration

Settings come from CLI flags, environment variables, or a repo-local
`.env`. Copy [`.env.example`](.env.example) to `.env` and fill in your
credentials — `.env` is gitignored, and the pre-commit `gitleaks` hook
runs locally against staged changes so secrets do not reach the history.

### Providers

Semia routes synthesis through one of four providers — two HTTP wire
formats and two local CLI shell-outs. The default is `responses` with
model `gpt-5.5`, authenticated via `OPENAI_API_KEY`.

| Provider     | Transport                          | Default model       | Honors `--base-url` | Auth                                                              |
| ------------ | ---------------------------------- | ------------------- | ------------------- | ----------------------------------------------------------------- |
| `responses`  | OpenAI Responses API (raw HTTP)    | `gpt-5.5`           | yes                 | `OPENAI_API_KEY`; `OPENAI_BASE_URL` (defaults to api.openai.com)  |
| `anthropic`  | Anthropic Messages API (raw HTTP)  | `claude-opus-4-7`   | yes                 | `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN`; `ANTHROPIC_BASE_URL` |
| `codex`      | shells out to `codex exec`         | Codex CLI's own     | no                  | inherits Codex CLI config                                         |
| `claude`     | shells out to `claude --print`     | `claude-opus-4-7`   | no                  | inherits Claude Code env (`ANTHROPIC_*`)                          |

`openai` is accepted as a synonym for `responses`. The **model** is free-form
— any string the endpoint accepts works (`gpt-5.5`, `gpt-5.4`,
`gpt-5.3-codex`, `deepseek-v4`, `claude-opus-4-7`, `claude-opus-4-6`, …).

Switch with flags:

```bash
# Default: OpenAI Responses against api.openai.com
semia scan ./some-skill --out .semia/runs/some-skill

# Anthropic Messages against api.anthropic.com
semia scan ./some-skill --out .semia/runs/some-skill --provider anthropic

# Point the responses format at a different endpoint (DeepSeek, OpenRouter, vLLM, …)
semia scan ./some-skill --out .semia/runs/some-skill \
  --provider responses --model deepseek-v4 \
  --base-url https://api.deepseek.com/v1

# Use the locally-installed Claude Code CLI (model is the only knob)
semia scan ./some-skill --out .semia/runs/some-skill --provider claude --model claude-opus-4-7
```

### Most common environment variables

| Variable                    | Purpose                                                              |
| --------------------------- | -------------------------------------------------------------------- |
| `SEMIA_LLM_PROVIDER`        | `responses` (default) / `anthropic` / `codex` / `claude`             |
| `SEMIA_LLM_MODEL`           | free-form model name passed to the provider                          |
| `SEMIA_LLM_TIMEOUT`         | request timeout in seconds                                           |
| `SEMIA_LLM_MAX_RETRIES`     | retry budget for transient provider errors                           |
| `OPENAI_BASE_URL`           | base URL for the `responses` provider                                |
| `ANTHROPIC_BASE_URL`        | base URL for the `anthropic` provider                                |
| `SEMIA_DETECTOR_BACKEND`    | `auto` (default), `souffle`, `builtin`                               |
| `SEMIA_SOUFFLE_BIN`         | path to `souffle` if not on `PATH`                                   |

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

The Codex and Claude Code plugin bundles under `packages/semia-plugins/<host>/`
ship with a self-contained `bin/semia.pyz` zipapp, so they work out of the
box without a separate `pip install semia`. The OpenClaw skill
relies on the published `semia` CLI on `PATH` (ClawHub provisions it via
`uv tool install`). Installing the Python package as well is recommended if
you want `semia` available as a normal shell command alongside the in-host
workflow.

**Codex** — pick either path.

*Shell (scripts and CI):*

```bash
codex plugin marketplace add berabuddies/Semia
```

*Interactive plugin manager inside the Codex CLI:*

1. Launch `codex`.
2. Inside Codex, input `/plugins` (plural — opens the plugin panel).
3. Press **←** (Left) to enter **Add marketplace**.
4. Enter `berabuddies/Semia`.
5. Back in the plugin panel, install `semia` from the newly-added
   marketplace.

Headless setups can enable the plugin directly by adding the following to
`~/.codex/config.toml`:

```toml
[plugins."semia@semia"]
enabled = true
```

**Claude Code** — pick either path.

*Shell (scripts and CI):*

```bash
claude plugin marketplace add berabuddies/Semia
claude plugin install semia@semia
```

*Interactive plugin manager inside the Claude Code CLI:*

1. Launch `claude`.
2. Inside Claude Code, input `/plugins` (plural — opens the plugin panel).
3. Press **→** (Right) twice and select **Add Marketplace**.
4. Enter `berabuddies/Semia`.
5. Back in the plugin panel, install `semia` from the newly-added marketplace.

The `name@marketplace` form on `install` is required — the second `semia`
is the marketplace identifier from the project's `marketplace.json`.
Use `--scope user|project|local` on the shell form to control where the
plugin is recorded (default is `user`):

```bash
claude plugin install semia@semia --scope project
```

See [Discover and install plugins](https://code.claude.com/docs/en/discover-plugins)
for the full UX and [Plugins reference](https://code.claude.com/docs/en/plugins-reference#cli-commands-reference)
for the complete list of `claude plugin ...` subcommands.

**OpenClaw** — install from ClawHub:

```bash
openclaw plugins install clawhub:semia
```

ClawHub will install the `semia` CLI on demand via `uv tool install
semia` (declared in the skill's `install` block). If you prefer to
pre-provision it yourself:

```bash
uv tool install semia   # or: pip install semia
openclaw plugins install clawhub:semia
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

## Project background

The technique behind Semia is described in the Semia paper
([arXiv:2605.00314](https://arxiv.org/abs/2605.00314) ·
[PDF](https://arxiv.org/pdf/2605.00314)). Semia is the
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

Semia is released under the [Apache License 2.0](LICENSE). You
may use, modify, and redistribute it freely, including for commercial
purposes, subject to the terms of the license. See [NOTICE](NOTICE) for
attribution.

The names **"Semia"**, **"Semia"**, **"Semia"**, and
**"berabuddies"** are trademarks of berabuddies and are **not** licensed under
Apache-2.0. See [TRADEMARKS.md](TRADEMARKS.md) for the trademark policy.
