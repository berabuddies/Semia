# Agent Coordination Patterns

How agents in a council work together without stepping on each other.

## Core Principle: File-Based Communication

Agents don't message each other directly. They communicate through shared files and directories. This is simple, traceable, and doesn't require complex orchestration.

## The Coordinator Role

The user's main assistant (the one running OpenClaw) is the coordinator. It:
- Routes incoming tasks to the right agent
- Reads one agent's output and feeds it to another when needed
- Resolves conflicts between agents
- Maintains the routing table in root AGENTS.md

Agents themselves never decide to hand off to another agent. The coordinator does that.

## File Coordination Map

Every council has a coordination map that defines data flow:

```
[Agent A] writes → shared/reports/[a]/
[Agent B] reads shared/reports/[a]/ → writes agents/[b]/output/
[Agent C] reads agents/[b]/output/ → writes agents/[c]/output/
```

**Rules:**
- Each agent writes ONLY to its own directories and shared directories
- Agents can READ from any other agent's output or shared directories
- The shared directory (`shared/`) is readable by all agents
- Each agent's workspace is owned by that agent

## Typical Coordination Patterns

### Research → Content Pipeline
```
Research agent writes intel → shared/reports/research/
Content agent reads intel → writes drafts in agents/content/drafts/
User reviews and approves drafts
```

### Research → Finance Pipeline
```
Research agent writes market data → shared/reports/research/
Finance agent reads data → writes analysis in agents/finance/analysis/
```

### Multi-Agent Task (3+ agents)
```
1. Coordinator receives complex task
2. Coordinator identifies which agents are needed
3. Research agent gathers data first (if needed)
4. Specialist agents work in parallel or sequence
5. Coordinator assembles final output
```

### Cross-Agent Learning
```
Any agent discovers a broadly useful learning
→ Writes to shared/learnings/CROSS-AGENT.md
→ Other agents check this file during periodic review
```

## Directory Structure

```
workspace/
├── agents/
│   ├── [agent-a]/
│   │   ├── SOUL.md
│   │   ├── AGENTS.md
│   │   ├── memory/
│   │   ├── .learnings/
│   │   └── [role-specific dirs]/
│   └── [agent-b]/
│       └── ...
├── shared/
│   ├── reports/
│   │   └── [agent-name]/      # Each agent's shared outputs
│   └── learnings/
│       └── CROSS-AGENT.md     # Cross-agent learnings
├── AGENTS.md                   # Root routing and coordination
├── SOUL.md                     # Main assistant identity
└── TOOLS.md                    # Shared tool knowledge
```

## Routing Table Format

The root AGENTS.md contains a routing table:

```markdown
| Task Type | Agent | Read |
|-----------|-------|------|
| [task category] | **[Name]** | `agents/[name]/SOUL.md` |
```

This table is how the coordinator knows where to send each task.

## Conflict Resolution

When multiple agents could handle a task:
1. The more specific agent wins (finance question about content revenue → finance agent, not content agent)
2. If truly ambiguous, coordinator picks one and notes the edge case
3. Edge cases get documented in root AGENTS.md under "Edge Cases"

## Scaling Considerations

- **3-4 agents**: Simple flat coordination, minimal shared state
- **5-7 agents**: Need explicit coordination map, shared directories become important
- **7+ agents**: Consider grouping agents into sub-teams with team leads (not recommended for most users)
