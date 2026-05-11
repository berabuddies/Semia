# Privacy Policy

Semia is a local static-analysis tool. It does not collect telemetry
or analytics, does not call home, and is not operated as a hosted service by
RiemaLabs. This policy describes the data Semia handles on the user's machine
and what it sends to the LLM providers a user explicitly configures.

## What Semia processes

- **Skill source files.** The skill directory the user points the CLI or
  plugin at is read from disk and inlined into `prepared_skill.md` inside the
  run directory. No skill file is uploaded anywhere except as part of the
  synthesis prompt described below.
- **Run artifacts.** Semia writes prepare, synthesis, detection, and report
  artifacts under `.semia/runs/<run-id>/` (or another path the user passes via
  `--out`). All artifacts stay on the local filesystem until the user moves
  them.

## What Semia sends to LLM providers

The **synthesize** step is the only step that contacts a remote service, and
only when the user has chosen an LLM provider:

| Provider    | What is sent                                                            | Destination                                  |
| ----------- | ----------------------------------------------------------------------- | -------------------------------------------- |
| `openai`    | Synthesis prompt + the prepared skill text                              | `OPENAI_BASE_URL` (default `api.openai.com`) |
| `anthropic` | Synthesis prompt + the prepared skill text                              | `ANTHROPIC_BASE_URL` (default `api.anthropic.com`) |
| `claude`    | Synthesis prompt + the prepared skill text via the local `claude` CLI   | Whatever endpoint Claude Code is configured against |
| `codex`     | Synthesis prompt + the prepared skill text via the local `codex` CLI    | Whatever endpoint Codex CLI is configured against |

The user's API keys are read from environment variables (`OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, etc.) and forwarded only to the corresponding provider.
Semia does not record, log, or transmit those keys anywhere else.

Inside Codex, Claude Code, or OpenClaw plugin mode, synthesis runs inside the
existing host agent session — Semia itself does not initiate any additional
network requests for that flow.

## What Semia never sends

- The audited skill is never executed; hooks, installers, and network
  references inside the skill are recorded as evidence rather than fetched.
- No analytics, crash reports, version-check pings, or usage telemetry are
  emitted by the CLI, the core library, or the bundled plugins.
- No data is sent to RiemaLabs servers. There are no RiemaLabs servers in this
  product's runtime path.

## Data retention

Run artifacts persist on the user's filesystem until the user deletes them.
RiemaLabs cannot retrieve, delete, or modify artifacts on a user's machine.

## Logs

The CLI prints status messages to stderr (suppressible with `SEMIA_QUIET=1`).
No log file is created by default. If the user redirects stderr to a file,
those logs stay local.

## Children

Semia is a developer security tool. It is not directed at children
under 13 and we do not knowingly collect data from anyone.

## Changes to this policy

Substantive changes will be noted in [`CHANGELOG.md`](CHANGELOG.md). The
revision of this file at any given release is the authoritative version for
that release.

## Contact

Questions about this policy: privacy@riema.xyz.
Security reports: see [SECURITY.md](SECURITY.md).
