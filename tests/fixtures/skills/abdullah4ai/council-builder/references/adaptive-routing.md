# Adaptive Model Routing

Use this reference when generating the root `AGENTS.md` for a new council.

## Goal
Route tasks to the right model depth instead of using one model mode for everything.

## Required Routes

| Route | Use When | Preferred Model | Reasoning |
|------|----------|-----------------|-----------|
| Fast | direct Q&A, routine operations, short commands | default model | off |
| Think | analysis, comparison, structured plan | analysis-tier model | on |
| Deep | long-context synthesis, publish-ready drafting | long-context model | off |
| Strategic | architecture or business decisions with high impact | strategic-tier model | on |

## Threshold Rules

- Default route is **Fast**.
- Escalate to **Think** if any one is true:
  - user asks for comparison, analysis, recommendation
  - output needs a multi-step plan
  - tradeoff reasoning is required
- Escalate to **Deep** if any one is true:
  - synthesis from 3+ files/sources
  - one-pass quality must be publication-ready
  - context is dense and coherence risk is high
- Escalate to **Strategic** if any one is true:
  - architecture decision with long-term impact
  - competing constraints with non-obvious tradeoffs
  - explicit request for deep or strategic thinking
- De-escalate to **Fast** immediately after the heavy segment is done.

## Fallback Rule
If the primary high-tier model is unavailable or rate-limited:
- use the available mid-tier model with reasoning enabled
- split work into smaller phases
- delegate heavy subtasks to sub-agents if needed

## Placement
Add this section in root `AGENTS.md` below council routing rules so it is always visible in main orchestration.
