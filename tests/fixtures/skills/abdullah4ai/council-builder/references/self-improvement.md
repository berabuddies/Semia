# Self-Improvement System

Every agent in the council has a built-in learning loop. This is not optional.

## Architecture

```
agents/[name]/.learnings/
├── LEARNINGS.md          # Corrections, knowledge gaps, best practices
├── ERRORS.md             # Command failures, unexpected behavior
└── FEATURE_REQUESTS.md   # Capabilities the user wished for
```

Plus a shared cross-agent file:
```
shared/learnings/CROSS-AGENT.md   # Learnings that apply to multiple agents
```

## How It Works

### Detection: When to Log

**Corrections** (→ LEARNINGS.md, category: correction):
- User says "no, that's wrong" or corrects the output
- Agent realizes its initial approach was incorrect
- Information turns out to be outdated

**Errors** (→ ERRORS.md):
- Command returns non-zero exit code
- API call fails or returns unexpected data
- Tool produces wrong output
- Timeout or connection failure

**Knowledge Gaps** (→ LEARNINGS.md, category: knowledge_gap):
- User provides information the agent didn't have
- Documentation referenced was outdated
- Behavior differs from expectation

**Best Practices** (→ LEARNINGS.md, category: best_practice):
- Found a better way to do a recurring task
- Discovered a pattern that saves time
- User praised a particular approach

**Feature Requests** (→ FEATURE_REQUESTS.md):
- User asks "can you also..."
- User says "I wish you could..."
- Missing capability identified during a task

### Logging Format

Each entry follows this structure:

```markdown
## [TYPE-YYYYMMDD-XXX] category_or_name

**Logged**: ISO-8601 timestamp
**Priority**: low | medium | high | critical
**Status**: pending

### Summary
One-line description

### Details
What happened, what was wrong, what's correct

### Suggested Action
Specific fix or improvement

### Metadata
- Source: conversation | error | user_feedback
- Related Files: path/to/file
- Tags: tag1, tag2
```

Type prefixes: `LRN` (learning), `ERR` (error), `FEAT` (feature request).

### Promotion: When Learnings Graduate

Learnings start in `.learnings/` but can be promoted when they prove broadly useful:

| Learning applies to... | Promote to |
|------------------------|------------|
| Agent personality/style | Agent's `SOUL.md` |
| Workflow patterns | Agent's `AGENTS.md` or root `AGENTS.md` |
| Tool usage gotchas | `TOOLS.md` |
| Multiple agents | `shared/learnings/CROSS-AGENT.md` |

**Promotion criteria:**
- Same learning appears 3+ times → auto-promote
- High priority + resolved → consider promotion
- User explicitly says "remember this" → promote immediately

When promoting:
1. Distill the learning into a concise rule
2. Add to the target file in the right section
3. Mark original entry as `**Status**: promoted`
4. Add `**Promoted**: [target file]`

### Resolution: Closing the Loop

When a learning is addressed:

```markdown
### Resolution
- **Resolved**: ISO-8601 timestamp
- **Notes**: What was done to fix it
```

Status values: `pending` → `in_progress` → `resolved` | `wont_fix` | `promoted`

## SOUL.md Integration

Every agent's SOUL.md must include a Self-Improvement section:

```markdown
## Self-Improvement
1. Review `.learnings/LEARNINGS.md` before major tasks in your domain
2. Log new learnings when:
   - [Domain-specific trigger 1]
   - [Domain-specific trigger 2]
   - [Domain-specific trigger 3]
   - User corrects any output
3. Learnings recurring 3+ times get promoted to this file
4. Share cross-agent learnings in `shared/learnings/CROSS-AGENT.md`
```

The triggers should be specific to the agent's domain:
- Research agent: "source turned out unreliable", "depth was wrong"
- Dev agent: "bug took long to find", "better library discovered"
- Content agent: "draft rejected with reason", "post performed unexpectedly"
- Finance agent: "calculation was off", "missed a cost factor"
- Ops agent: "reminder was wrong time", "email tone was off"

## Periodic Review

Agents should review their learnings at natural breakpoints:
- Before starting a major task in their domain
- After completing a significant project
- When working in an area with past learnings

Quick status check patterns:
```bash
# Count pending items
grep -c "Status\*\*: pending" agents/[name]/.learnings/*.md

# Find high-priority pending
grep -B5 "Priority\*\*: high" agents/[name]/.learnings/*.md | grep "^## \["
```

## Weekly Metrics Layer

In addition to `.learnings/`, every council should include:

`memory/learning-metrics.json`

Recommended schema:
```json
{
  "lastWeeklyReview": null,
  "windowDays": 7,
  "counts": {
    "errors": 0,
    "learnings": 0,
    "featureRequests": 0,
    "repeatedMistakes": 0,
    "promotions": 0
  },
  "routing": {
    "fast": 0,
    "think": 0,
    "deep": 0,
    "strategic": 0
  },
  "nextWeekFocus": ""
}
```

Weekly review checklist:
1. Count new entries in ERRORS, LEARNINGS, FEATURE_REQUESTS
2. Count repeated mistakes (same issue appears 2+ times)
3. Count promotions to permanent files
4. Track route distribution (Fast/Think/Deep/Strategic)
5. Set one concrete next-week focus

## Initialization

When creating a new agent, initialize .learnings/ with empty files using the templates from `assets/LEARNINGS-TEMPLATE.md`. The files should have headers and status definitions but no entries yet.
Also initialize `memory/learning-metrics.json` using `assets/LEARNING-METRICS-TEMPLATE.json`.
