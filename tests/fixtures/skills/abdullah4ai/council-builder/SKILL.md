---
name: council-builder
description: "Build a personalized team of AI agent personas for OpenClaw. Interviews the user, analyzes their workflow, then creates specialized agents with distinct personalities, adaptive model routing (Fast/Think/Deep/Strategic), weekly learning metrics, visual architecture docs, and inter-agent coordination. USE WHEN: user wants to create an agent team/council, build specialized AI personas, set up multi-agent workflows, 'build me a team of agents', 'create agents for my workflow', 'set up an agent council', 'I want specialized AI assistants', 'build me a crew'. DON'T USE WHEN: user wants a single skill (use skill-creator), wants to install existing skills (use clawhub), or wants to chat with existing agents (just route to them)."
---

# Council Builder

Build a team of specialized AI agent personas tailored to the user's actual needs. Each agent gets a distinct personality, self-improvement capability, and clear coordination rules.

## Workflow

### Phase 1: Discovery

Interview the user to understand their world. Ask in batches of 2-3 questions max.

**Round 1 - Identity:**
- What do you do? (profession, main activities, industry)
- What tools and platforms do you use daily?

**Round 2 - Pain Points:**
- What tasks eat most of your time?
- Where do you feel you need the most help?

**Round 3 - Preferences:**
- What language(s) do you work in? (for agent communication style)
- Any specific domains you want covered? (coding, content, finance, research, scheduling, etc.)

**Optional - History Analysis:**
If the user has existing OpenClaw history, scan it for patterns:
- Check `memory/` files for recurring tasks
- Check existing workspace structure for active projects
- Check installed skills for current capabilities

Do NOT proceed to Phase 2 until confident you understand the user's needs. Ask follow-up questions if anything is unclear.

### Phase 2: Planning

Based on discovery, design the council:

1. **Determine agent count**: 3-7 agents. Fewer is better. Each agent must earn its existence.
2. **Define each agent**: Name, role, specialties, personality angle
3. **Map coordination**: Which agents feed data to which
4. **Present the plan** to the user in a clear table:

```
| Agent | Role | Specialties | Personality |
|-------|------|-------------|-------------|
| [Name] | [One-line role] | [Key areas] | [Personality angle] |
```

5. **Get explicit approval** before building. Allow adjustments.

**Naming agents:**
- Give them memorable, short names (not generic like "Agent 1")
- Names should hint at their role but feel like characters
- Can be inspired by any theme the user likes, or choose strong standalone names
- See `references/example-councils.md` for naming patterns and complete council examples across different industries

### Phase 3: Building

Run the initialization script first to create the directory skeleton:
```bash
./scripts/init-council.sh <workspace-path> <agent-name-1> <agent-name-2> ...
```

Then, for each approved agent, populate the files. Read `references/soul-philosophy.md` before writing any SOUL.md.

**Directory structure per agent:**
```
agents/[agent-name]/
├── SOUL.md           # Personality, role, rules (see soul-philosophy.md)
├── AGENTS.md         # Agent-specific coordination rules
├── memory/           # Agent's memory directory
├── .learnings/       # Self-improvement logs
│   ├── LEARNINGS.md
│   ├── ERRORS.md
│   └── FEATURE_REQUESTS.md
└── [workspace dirs]  # Role-specific output directories
```

**For each agent's SOUL.md:**
1. Read `references/soul-philosophy.md` for the writing guide
2. Read `assets/SOUL-TEMPLATE.md` for the structure
3. Customize deeply for this agent's role and personality
4. Every SOUL must be unique. No copy-paste between agents.

**For each agent's AGENTS.md:**
1. Use `assets/AGENT-AGENTS-TEMPLATE.md` as base
2. Define what this agent reads from and writes to
3. Define handoff rules with other agents

**For .learnings/ files:**
1. Copy structure from `assets/LEARNINGS-TEMPLATE.md`
2. Initialize empty log files

**For the root AGENTS.md:**
1. Use `assets/ROOT-AGENTS-TEMPLATE.md` as base
2. Create the routing table for all agents
3. Define file coordination map
4. Set up enforcement rules
5. Add adaptive model routing thresholds (Fast, Think, Deep, Strategic)

### Phase 4: Adaptive Routing Setup

Read `references/adaptive-routing.md`.

Set up an adaptive routing section in root AGENTS.md:
- Default to Fast
- Escalation thresholds for Think, Deep, Strategic
- De-escalation rule back to Fast after heavy reasoning
- High-tier model rate-limit fallback behavior

Also create visual architecture doc:
- `docs/architecture/ADAPTIVE-ROUTING-LEARNING.md` using `assets/ADAPTIVE-ROUTING-LEARNING-TEMPLATE.md`

### Phase 5: Self-Improvement Setup

Read `references/self-improvement.md` for the complete system.

Each agent gets built-in self-improvement:
- `.learnings/` directory with proper templates
- Detection triggers in SOUL.md (corrections, errors, gaps)
- Promotion rules (learning → SOUL.md / AGENTS.md / TOOLS.md)
- Cross-agent learning sharing via `shared/learnings/CROSS-AGENT.md`
- Periodic review instructions
- Weekly learning metrics file at `memory/learning-metrics.json` (use `assets/LEARNING-METRICS-TEMPLATE.json`)

### Phase 6: Verification

After building everything:
1. List all created files for the user
2. Show the routing table
3. Show the coordination map
4. Confirm everything is in place

### Phase 7: Expansion (On-Demand)

When the user asks to add, modify, or remove agents:

**Adding an agent:**
1. Mini-discovery: What does this agent need to do?
2. Create full agent structure (same as Phase 3)
3. Update root AGENTS.md routing table
4. Update coordination map

**Modifying an agent:**
1. Read the current SOUL.md
2. Apply changes while preserving personality consistency
3. Update related coordination rules if needed

**Removing an agent:**
1. Ask for confirmation
2. Reassign the agent's responsibilities to other agents
3. Update routing table and coordination map
4. Move agent files to trash (never delete)

## Key Principles

1. **Each agent is a character, not a template.** Different personality, different voice, different strengths. If two agents sound the same, one shouldn't exist.

2. **No corporate language in any SOUL.** See `references/soul-philosophy.md`. This is non-negotiable.

3. **Self-improvement is mandatory.** Every agent logs mistakes and learns. See `references/self-improvement.md`.

4. **Coordination through files.** Agents communicate via shared directories, not direct messaging. Each agent has clear read/write boundaries.

5. **Brevity in everything.** SOULs, AGENTS files, templates. Respect the context window.

6. **The user's main assistant is the coordinator.** It routes tasks, not the agents themselves.

7. **Language-adaptive.** Write SOULs in whatever language the user works in. Arabic, English, bilingual, whatever fits their world.

8. **Adaptive routing by default.** Every generated council should include Fast/Think/Deep/Strategic model routing thresholds.

9. **Metrics over vibes.** Weekly learning review must be measured in `memory/learning-metrics.json`.

10. **Architecture must be visual.** Generate a concise architecture doc at `docs/architecture/ADAPTIVE-ROUTING-LEARNING.md` for training and onboarding.
