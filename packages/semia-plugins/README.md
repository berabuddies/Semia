# Semia Plugins

Semia is distributed as Skill Behavior Mapping tooling plus host integrations.
These packages expose the same audit workflow to Codex, Claude Code, and
OpenClaw while sharing one canonical `semia` skill.

```text
shared/skills/semia/SKILL.md  canonical workflow
codex/                                  Codex plugin package
claude-code/                            Claude Code plugin package
openclaw/                               OpenClaw plugin package
```

The deterministic Semia CLI prepares, synthesizes, detects, and reports. The
current host agent session writes synthesized SDL facts with typed
`*_evidence_text(...)` facts.
