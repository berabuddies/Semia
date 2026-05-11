# Semia Architecture

Semia is built around Skill Behavior Mapping: converting an agent skill into a
compact, checkable behavior map before deterministic detection.

Semia is split into three layers:

```text
semia-core      deterministic analysis contracts and detectors
semia-cli       command surface for prepare/synthesize/detect/report
semia-plugins   Codex, Claude Code, and OpenClaw integration packages
```

The core idea is not the wrapper. It is the behavior map. Integrations are
distribution surfaces that can use the current agent session for synthesis
instead of embedding a provider client.

## Data Flow

```text
SkillInput
  -> PreparedSkill
  -> SynthesisPrompt
  -> RawFactProgram
  -> CheckedFactProgram
  -> EvidenceBundle
  -> CoreFactProgram
  -> DetectionResult
  -> AuditReport
```

Each step communicates through artifacts, not in-process detector coupling. This
keeps CLI, CI, and host integrations aligned while allowing detectors and report
renderers to evolve independently.

## Prepare

Prepare is deterministic. It reads skill markdown and auxiliary source files,
inlines them, normalizes reference units, and assigns stable evidence handles.
It also records a file inventory and source map so reports and future tooling
can trace prepared lines back to original files.

Primary outputs:

- `prepared_skill.md`
- `prepare_metadata.json`
- `prepare_units.json`

Prepare does not infer control flow, data flow, triggers, effects, or policy
labels.

## Synthesize

Synthesize builds the behavior map. In host integrations, it is performed by
the current agent session. The agent reads prepared artifacts and writes
`synthesized_facts.dl`.

The program contains:

- core SDL facts used by detectors
- typed `*_evidence_text(...)` sidecar facts used for grounding

The agent never emits normalized `su_*` handles. Semia's deterministic aligner
maps evidence text to prepared reference units.

## Detect

Detect is deterministic. It consumes the checked core fact program, runs
Souffle-backed Datalog derivations and detectors, and renders findings. Evidence
is available to reports and scoring, but the default detectors consume core
facts only.

## Integration Packages

The repository ships three host integration packages:

- `packages/semia-plugins/codex`
- `packages/semia-plugins/claude-code`
- `packages/semia-plugins/openclaw`

All host packages share the same canonical audit workflow under:

```text
packages/semia-plugins/shared/skills/semia/SKILL.md
```

Host-specific skill files are thin wrappers around the shared workflow and keep
manifest metadata near the host packaging format.

## Supply Chain Boundary

Semia may ship a limited Souffle fallback runtime later, but detector execution
should remain behind the CLI/runtime boundary. A fallback runtime should be
pinned by platform, checksum, license metadata, and provenance, and users should
be able to override it with an explicit `SEMIA_SOUFFLE_BIN`.
