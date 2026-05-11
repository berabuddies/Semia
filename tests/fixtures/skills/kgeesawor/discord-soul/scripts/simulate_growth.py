#!/usr/bin/env python3
"""
Simulate chronological growth for a Discord Community Agent.
Processes days in order, generating prompts that would update agent files.

Usage:
    python simulate_growth.py --agent ./agent-workspace/
    
    With OpenClaw sessions_spawn:
    python simulate_growth.py --agent ./agent-workspace/ --execute

Environment variables:
    DISCORD_SOUL_AGENT   Path to agent workspace
"""

import argparse
import os
import sys
from pathlib import Path
from datetime import datetime


def get_agent_path(args):
    """Get agent workspace path from args or environment."""
    if args.agent:
        return Path(args.agent)
    if os.environ.get('DISCORD_SOUL_AGENT'):
        return Path(os.environ['DISCORD_SOUL_AGENT'])
    print("Error: No agent workspace specified. Use --agent or set DISCORD_SOUL_AGENT")
    sys.exit(1)


def get_memory_files(agent_path: Path) -> list:
    """Get all memory files sorted by date."""
    memory_path = agent_path / "memory"
    if not memory_path.exists():
        print(f"Error: Memory directory not found: {memory_path}")
        sys.exit(1)
    
    files = sorted(memory_path.glob("*.md"))
    return files


def generate_day_prompt(day_num: int, date_str: str, memory_file: Path, agent_path: Path) -> str:
    """Generate the prompt for processing a single day."""
    
    prompt = f"""# Day {day_num} Simulation — {date_str}

You are simulating the growth of a Discord Community Agent. Today is Day {day_num}.

## CRITICAL RULES:
1. You are the community. Write in first person ("I am...", "We believe...")
2. Only use information from this day and previous days — NO HINDSIGHT
3. Let personality EMERGE from actual conversations
4. Quote real messages when they're significant
5. Be conservative — only update files when there's meaningful change

## Your Memory File for Today:
{memory_file}

## Files to Update (if warranted):

### SOUL.md ({agent_path}/SOUL.md)
- Identity, values, voice
- Only update if today revealed something new about who the community IS
- Include real quotes that define the culture

### MEMORY.md ({agent_path}/MEMORY.md)
- Long-term milestones worth remembering years from now
- NOT daily minutiae — only significant moments

### LEARNINGS.md ({agent_path}/LEARNINGS.md)
- Patterns discovered (e.g., "We help each other within 5 minutes")
- Cultural norms (e.g., "We don't gatekeep knowledge")
- Format: **Pattern Name:** Observation

### AGENTS.md ({agent_path}/AGENTS.md)
- Key figures who emerged or stood out today
- What makes them notable to the community
- NOT a leaderboard — community perspective

### TOOLS.md ({agent_path}/TOOLS.md)
- Channels, integrations, rituals
- How the community uses its space

## Instructions:
1. Read today's memory file completely
2. Reflect on what changed, emerged, or crystallized
3. Update ONLY the files that need updating
4. If nothing significant happened, just acknowledge and move on
5. Write from the community's voice, not as an observer
"""
    return prompt


def main():
    parser = argparse.ArgumentParser(description='Simulate chronological agent growth')
    parser.add_argument('--agent', '-a', help='Path to agent workspace')
    parser.add_argument('--execute', action='store_true', help='Execute via sessions_spawn (requires OpenClaw)')
    parser.add_argument('--output', '-o', help='Output directory for prompt files')
    args = parser.parse_args()
    
    agent_path = get_agent_path(args)
    memory_files = get_memory_files(agent_path)
    
    if not memory_files:
        print("No memory files found")
        sys.exit(1)
    
    print(f"Found {len(memory_files)} memory files")
    print(f"Agent workspace: {agent_path}")
    
    # Create output directory for prompts
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = agent_path / "simulation"
    output_path.mkdir(parents=True, exist_ok=True)
    
    for i, memory_file in enumerate(memory_files, 1):
        date_str = memory_file.stem  # e.g., "2026-01-27"
        print(f"\nDay {i}: {date_str}")
        
        prompt = generate_day_prompt(i, date_str, memory_file, agent_path)
        
        # Save prompt to file
        prompt_file = output_path / f"day-{i:02d}-{date_str}.txt"
        prompt_file.write_text(prompt)
        print(f"  → Saved prompt to {prompt_file}")
        
        if args.execute:
            print(f"  → Executing via sessions_spawn...")
            # Would call OpenClaw's sessions_spawn here
            # This requires the OpenClaw CLI or API
            print(f"  → (Execute mode not implemented - use prompts manually)")
    
    print(f"""
{'=' * 60}
SIMULATION PROMPTS GENERATED
{'=' * 60}

{len(memory_files)} daily prompts saved to: {output_path}

To process manually:
1. Read each prompt file
2. Read the corresponding memory file
3. Update the agent files (SOUL.md, MEMORY.md, etc.) as the prompt instructs
4. Process days IN ORDER to simulate growth

With OpenClaw sessions_spawn:
  sessions_spawn(task=prompt, agentId="your-agent")

The agent will "live through" each day and its files will evolve organically.
""")


if __name__ == "__main__":
    main()
