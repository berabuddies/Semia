# Advanced Usage

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
5. **Repair** *(optional)* — trace each finding back through the Datalog
   rules to identify which facts caused it, then call an LLM to generate
   a SKILL.md patch. The patch either fixes the problematic content
   (e.g. replacing a hardcoded IP) or adds specific security constraints
   (e.g. "Never execute `blockchain.send_transaction()` without user
   confirmation"). The tracer and prompt builder are deterministic; only
   the patch generation step calls the LLM.

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
semia scan ./some-skill

# Anthropic Messages against api.anthropic.com
semia scan ./some-skill --provider anthropic

# Point the responses format at a different endpoint (DeepSeek, OpenRouter, vLLM, …)
semia scan ./some-skill \
  --provider responses --model deepseek-v4 \
  --base-url https://api.deepseek.com/v1

# Use the locally-installed Claude Code CLI (model is the only knob)
semia scan ./some-skill --provider claude --model claude-opus-4-7
```

Each of these lands output under `.semia/runs/some-skill/`. Pass
`--out <path>` if you want a custom run directory.

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
semia scan ./some-skill --prepare-only
```

**Reuse facts from a prior run or an agent session:**
```bash
semia scan ./some-skill --facts synthesized_facts.dl
semia report .semia/runs/some-skill --format sarif
```

**Repair a scanned skill (generate SKILL.md patch):**
```bash
# From an existing scan run:
semia repair .semia/runs/some-skill --from-scan

# Scan + repair in one shot:
semia repair ./some-skill

# Trace only (see what to fix, without generating patches):
semia repair .semia/runs/some-skill --from-scan --trace-only
```

`repair` keeps the audit report at `.semia/runs/some-skill/report.md`
and writes the proposed patch to
`.semia/runs/some-skill/patched/SKILL.md`. After reviewing the patch,
copy it into a sibling skill directory like this:

```bash
mkdir -p some-skill_patched && cp .semia/runs/some-skill/patched/SKILL.md some-skill_patched/SKILL.md
```

The CLI prints the exact command for the path you scanned.
