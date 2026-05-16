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
pip install semia-audit
semia scan ./some-skill
```

`scan` does prepare → synthesize (via your configured LLM provider) →
detect → report in one shot. Output lands under
`.semia/runs/<skill-slug>/` by default — pass `--out <path>` to override.
You'll need an LLM provider configured first — see
[Set up an LLM provider](#set-up-an-llm-provider) below.

### Inside Codex, Claude Code, or OpenClaw

Install the plugin once. Each host has its own flow.

**Codex** — pick either path:

*Shell (scripts and CI):*

```bash
codex plugin marketplace add berabuddies/Semia
```

Then enable the plugin by appending to `~/.codex/config.toml`:

```toml
[plugins."semia@semia"]
enabled = true
```

*Interactive plugin manager inside the Codex CLI:*

1. Launch `codex`.
2. Inside Codex, input `/plugins` (plural — opens the plugin panel).
3. Press **←** (Left) to enter **Add marketplace**.
4. Enter `berabuddies/Semia`.
5. Back in the plugin panel, toggle `semia` on from the
   newly-added marketplace.

**Claude Code** — pick either path:

*Shell (one-liner):*

```bash
claude plugin marketplace add berabuddies/Semia
claude plugin install semia@semia
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

### Fix what Semia finds

```bash
semia repair .semia/runs/some-skill --from-scan
```

`repair` reads the findings and synthesized facts from an existing scan,
traces each violation back through the Datalog rules to identify the root
cause, then calls an LLM to generate a SKILL.md patch — either fixing
the problematic content directly or adding specific security constraints.

```bash
# Or scan + repair in one shot:
semia repair ./some-skill
```

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

See [Configuration](ADVANCED_USAGE.md#configuration) for the full provider
matrix, base-URL support, timeout/retry knobs, and synthesis-loop tuning.

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
| `repair_result.json`      | repair outcomes (when `semia repair` is run)       |
| `patched/SKILL.md`        | the repaired SKILL.md (when `semia repair` is run) |

</details>

## More docs

- [Advanced usage](ADVANCED_USAGE.md) covers the worked example, trust
  model, installation, configuration, and common workflows.
- [Development](DEVELOPMENT.md) covers the repository layout and local
  development workflow.

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

## License

Semia is released under the [Apache License 2.0](LICENSE).
Copyright 2026 RiemaLabs.

## Citation

If you use this tool, please cite our paper:

```bibtex
@misc{wen2026semia,
  title = {Semia: Auditing Agent Skills via Constraint-Guided Representation Synthesis},
  author = {Wen, Hongbo and Li, Ying and Liu, Hanzhi and Shou, Chaofan and Chen, Yanju and Tian, Yuan and Feng, Yu},
  year = {2026},
  eprint = {2605.00314},
  archivePrefix = {arXiv},
  primaryClass = {cs.CR},
  doi = {10.48550/arXiv.2605.00314},
  url = {https://arxiv.org/abs/2605.00314}
}
```
