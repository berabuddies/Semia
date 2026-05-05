# Semia Skillscan

Semia Skillscan builds a behavior map for AI agent skills. It turns
natural-language skill instructions and adjacent source into grounded facts
about what the skill may do, then runs deterministic checks over those facts.
It is maintained by RiemaLabs and follows the license used by the Semia paper:
[arXiv:2605.00314](https://arxiv.org/abs/2605.00314).

The product shape is:

```text
semia scan ./some-skill
Run Semia audit on this skill
```

The scanner is designed around a narrow trust boundary. Host agents such as
Codex, Claude Code, and OpenClaw can use their own session to synthesize the
behavior map, while Semia provides deterministic preparation, fact checking,
evidence grounding, Souffle-backed detection, and reporting.
The standalone CLI defaults to OpenAI for synthesis with `gpt-5.5`, using
`OPENAI_API_KEY`. Users can override the provider or model with flags or
environment variables.

## Quick start

In an installed plugin host, ask:

```text
Run Semia audit on this skill
```

From a shell, run a full local audit:

```bash
semia scan ./some-skill --out .semia/runs/some-skill
```

By default, this runs `prepare`, calls the configured LLM provider for
`synthesize`, then runs `detect` and `report`. The default provider is `openai`
and the default model is `gpt-5.5`. Use `--provider anthropic` for direct
Anthropic SDK calls, `--provider codex` or `--provider claude` to route
synthesis through a local agent CLI, or `--model` to pass an explicit model
name to the selected provider.

Configuration knobs:

```bash
export OPENAI_API_KEY=...
export SEMIA_LLM_PROVIDER=openai
export SEMIA_LLM_MODEL=gpt-5.5
semia scan ./some-skill --out .semia/runs/some-skill
```

Provider defaults:

- `openai`: reads `OPENAI_API_KEY`, optional `OPENAI_BASE_URL`, and streams the
  Responses API by default.
- `anthropic`: uses the Python Anthropic SDK when installed. It reads
  `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN`, optional
  `ANTHROPIC_BASE_URL`, and `ANTHROPIC_MODEL`.
- `claude`: shells out to Claude Code and inherits Claude Code environment such
  as `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL`, and
  `ANTHROPIC_MODEL`.
- `codex`: shells out to Codex CLI and inherits the user's Codex CLI
  configuration.

Shared Semia overrides:

- `SEMIA_LLM_PROVIDER`
- `SEMIA_LLM_MODEL`
- `SEMIA_LLM_TIMEOUT`
- `SEMIA_LLM_MAX_RETRIES`
- `SEMIA_SYNTHESIS_N_ITERATIONS`
- `SEMIA_SYNTHESIS_MAX_RETRIES`
- `SEMIA_SYNTHESIS_PLATEAU_MIN_IMPROVEMENT`
- `SEMIA_SYNTHESIS_PLATEAU_PATIENCE`
- `SEMIA_SYNTHESIS_RESUME_FROM`
- `SEMIA_SYNTHESIS_MAX_DOC_BYTES`

Synthesize writes production audit artifacts as it runs:

- `synthesized_facts.dl`: selected winning behavior map
- `synthesized_facts_<n>.dl`: accepted candidate per iteration
- `synthesis_attempt_<n>_<m>.dl`: raw extracted attempt facts
- `synthesis_patch_<n>_<m>.dl`: incremental review diff, when used
- `synthesis_response_<n>_<m>.txt`: raw provider response
- `synthesis_metadata.json`: provider, model, retry, score, candidate chain,
  selected iteration, and stop reason

For local development, simulate a fresh user install:

```bash
python3 -m venv --clear .venv
source .venv/bin/activate
python -m pip install -e .
semia --help
semia scan ./some-skill --out .semia/runs/some-skill
```

For direct Anthropic SDK synthesis, install the optional extra:

```bash
python -m pip install -e ".[anthropic]"
semia scan ./some-skill --out .semia/runs/some-skill --provider anthropic
```

If the virtual environment was created by a broken Python runtime, recreate it
with `python3 -m venv --clear .venv` before installing.

If you already have agent-generated synthesized facts, provide them explicitly:

```bash
semia scan ./some-skill --out .semia/runs/some-skill --facts synthesized_facts.dl
semia report .semia/runs/some-skill --format sarif
```

For CI smoke tests or offline demos only, `--offline-baseline` uses a
conservative non-LLM fallback. It is not a substitute for real synthesis. Use
`--prepare-only` only when you intentionally want to stop after prepare.

## Repository shape

```text
packages/
  semia-core/       # deterministic analysis library
  semia-cli/        # local and CI command surface
  semia-plugins/    # Codex, Claude Code, and OpenClaw integrations
docs/
  release.md
  supply-chain.md
tests/
```

This scaffold intentionally keeps runtime dependencies at zero. Package lanes
can add their own dependencies when they land, but the root quality gates stay
stdlib-friendly.

## Development

Install `uv`, then run:

```bash
make help
make check
make build
make release-check
```

The root checks currently cover:

- Python byte-compilation via `compileall`
- stdlib `unittest` discovery
- integration manifest JSON validation
- package metadata and package-data checks

## Behavior Map Contract

The target skill is untrusted data. A host agent may read skill contents to
synthesize behavior facts, but deterministic Semia tooling is the acceptance
boundary: generated facts must pass parsing, schema checks, evidence alignment,
and detector execution before a report is trusted.

## License

Semia Skillscan uses `CC-BY-NC-ND-4.0`, matching the Semia paper
([arXiv:2605.00314](https://arxiv.org/abs/2605.00314)). This is a
source-available research/software release, not an OSI open source software
license. Commercial use and distribution of modified versions require explicit
permission from RiemaLabs. See [LICENSE](LICENSE).
