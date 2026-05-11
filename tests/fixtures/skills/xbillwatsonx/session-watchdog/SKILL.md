---
name: session-watchdog
description: Monitor session context levels and proactively save checkpoints before compaction. Use when: (1) session context exceeds 80% capacity, (2) user asks about session status or memory, (3) at the start of each new session to check context, or (4) before long tasks that might push context over threshold.
---

# Session Watchdog

Monitors context levels, warns before compaction, and saves checkpoints to preserve important information.

## Context Thresholds

| Level | Tokens | Action |
|-------|--------|--------|
| Safe | 0-140k | Normal operation |
| **Warning** | 140k-160k | Warn user, save checkpoint |
| Critical | 160k-197k | Warn + stop unless urgent |
| Full | 197k+ | Compaction imminent |

## Check Context

Before each session and periodically during long conversations:

```
session_status
```

Check the `contextTokens` field from the response.

## Checkpoint Protocol

When approaching 80% (160k tokens):

1. **Save checkpoint to memory file:**
   - Read current memory/YYYY-MM-DD.md
   - Add key context: decisions, pending tasks, important details
   - Write back to memory file

2. **Alert user:**
   Say: "⚠️ Approaching context limit (~160k tokens). Saving checkpoint to memory before continuing."

3. **Ask user:**
   - Continue and accept compaction?
   - Summarize and restart fresh?
   - Pause until ready?

## What to Save

Essential information that must survive compaction:

- **Decisions made** in this conversation
- **Pending tasks** not yet completed
- **Important context** (project state, configurations, preferences)
- **Files modified** and their paths
- **Unresolved issues** requiring follow-up

## When to Trigger

- At session start
- After every 30k tokens of conversation
- Before initiating large tasks (file edits, multiple operations)
- When user asks "how much context do we have left?"

## Memory File Format

```
# YYYY-MM-DD

## Session Checkpoint (at X% context)

### Decisions
- Decision 1
- Decision 2

### Pending
- [ ] Task 1
- [ ] Task 2

### Important Context
- Project state: ...
- Last file modified: ...

### Unresolved
- Issue needing follow-up
```
