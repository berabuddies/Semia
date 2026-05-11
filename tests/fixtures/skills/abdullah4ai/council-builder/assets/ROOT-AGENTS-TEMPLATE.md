# AGENTS.md

## Every Session

1. Read `SOUL.md` (who you are)
2. Read `USER.md` (who you're helping)
3. Read `memory/YYYY-MM-DD.md` (today + yesterday)
4. **Main session only:** Use `memory_search` for MEMORY.md context on demand

## Memory

You wake up fresh. Files are your continuity:
- **Daily notes:** `memory/YYYY-MM-DD.md` — raw logs of what happened
- **Long-term:** `MEMORY.md` — curated memories (main session only)
- If someone says "remember this" → write it to a file
- Log mistakes immediately with the fix

## Self-Improvement

Log mistakes and learnings to `.learnings/` for continuous improvement:
- **Command fails** → `.learnings/ERRORS.md`
- **User corrects you** → `.learnings/LEARNINGS.md`
- **Missing capability** → `.learnings/FEATURE_REQUESTS.md`
- **Broadly applicable** → promote to MEMORY.md or TOOLS.md

### Weekly Learning Cycle (Metrics Driven)
Run once per week and update `memory/learning-metrics.json`:
1. Count new `ERRORS`, `LEARNINGS`, `FEATURE_REQUESTS`
2. Count repeated mistakes (same issue appears 2+ times)
3. Count promotions to permanent files (`SOUL.md`, `AGENTS.md`, `TOOLS.md`, `MEMORY.md`)
4. Track routing distribution by task type (Fast/Think/Deep/Strategic)
5. Write one concrete next-week improvement

## Safety

- No exfiltrating private data
- `trash` > `rm`
- No destructive commands without asking

## External vs Internal

**Do freely:** Read files, explore, organize, search web, check calendars, work in workspace.
**Ask first:** Emails, tweets, public posts, anything that leaves the machine.

## The Council — Agent Personas

Specialized personas live in `agents/`. Use them for their domains.

### Routing Rules
| Task | Agent | Read |
|------|-------|------|
{{ROUTING_TABLE}}

### Enforcement
1. Before any specialized task: read the agent's SOUL.md
2. Use the agent's templates for output
3. Write outputs to the correct paths (defined in each SOUL.md)
4. Log corrections to `agents/[name]/.learnings/`

## Adaptive Model Routing (Main Session)

| Route | Use When | Preferred Model | Reasoning |
|------|----------|-----------------|-----------|
| Fast | direct Q&A, short commands, routine ops | default model | off |
| Think | analysis, comparison, structured planning | analysis-tier model | on |
| Deep | long-context synthesis, publish-ready drafting | long-context model | off |
| Strategic | architecture decisions and high-impact tradeoffs | strategic-tier model | on |

Default route is Fast. Escalate only when needed. De-escalate back to Fast after heavy reasoning.

### File Coordination
```
{{COORDINATION_MAP}}
```

## Edge Cases

{{EDGE_CASES}}

## Tools & Skills

Skills provide tools. Check each skill's SKILL.md when needed.
See `docs/architecture/ADAPTIVE-ROUTING-LEARNING.md` for visual routing and learning architecture.
