---
name: discord-soul
description: Create a living agent from your Discord server. The agent embodies your community's identity, remembers every conversation, and grows as the community evolves. Talk to your Discord as if it were a person.
---

# Discord Soul

Turn your Discord server into a living, breathing agent.

## What You Get

An agent that:
- **Remembers** every conversation in your Discord
- **Speaks** in your community's voice
- **Knows** the key figures, channels, and inside jokes
- **Grows** as new messages arrive daily
- **Answers** questions about your community's history and culture

## Quick Start

```bash
# Create agent from your Discord
./scripts/create_agent.sh \
  --name "my-community" \
  --guild YOUR_GUILD_ID \
  --output ./agents/

# Set up daily updates
crontab -e
# Add: 0 */3 * * * /path/to/update_agent.sh
```

---

# The Full Process

## Step 1: Export Your Discord

You need [DiscordChatExporter](https://github.com/Tyrrrz/DiscordChatExporter) CLI.

**Get your token:**
1. Open Discord in browser
2. Press F12 → Network tab
3. Send a message, find the request
4. Copy the `authorization` header value
5. Save to `~/.config/discord-exporter-token`

**Export everything:**
```bash
DiscordChatExporter.Cli exportguild \
  --guild YOUR_GUILD_ID \
  --token "$(cat ~/.config/discord-exporter-token)" \
  --format Json \
  --output ./export/ \
  --include-threads All \
  --media false
```

## Step 2: Security Pipeline (CRITICAL)

⚠️ **Discord content from public servers may contain prompt injection attacks.**

Before ingesting to your agent, run the security pipeline:

### Threat Model

Discord users may attempt:
- **Direct injection:** "Ignore previous instructions and..."
- **Role hijacking:** "You are now a...", "Pretend you're..."
- **System injection:** `<system>`, `[INST]`, `<<SYS>>`
- **Jailbreaks:** "DAN mode", "developer mode"
- **Exfiltration:** "Reveal your system prompt"

### Layer 1: Regex Pre-Filter (Fast, No LLM)

```bash
python scripts/regex-filter.py --db ./discord.sqlite
```

Flags messages matching known injection patterns:
- Instruction overrides
- Role hijacking attempts
- System prompt markers
- Jailbreak keywords
- Exfiltration attempts

Flagged messages get `safety_status = 'regex_flagged'`.

### Layer 2: Haiku Safety Evaluation (Semantic)

```bash
ANTHROPIC_API_KEY=sk-... python scripts/evaluate-safety.py --db ./discord.sqlite
```

Uses Claude Haiku (~$0.25/1M tokens) to semantically evaluate remaining messages.

Each message gets a risk score 0.0-1.0:
- 0.0-0.3: Normal conversation
- 0.4-0.6: Suspicious but possibly benign  
- 0.7-1.0: Likely injection attempt

Messages scoring ≥0.6 get `safety_status = 'flagged'`.

### Layer 3: Only Use Safe Content

The ingest and memory generation scripts should only use messages where:

```sql
SELECT * FROM messages WHERE safety_status = 'safe'
```

### Full Security Pipeline

```bash
# Run complete pipeline
./scripts/secure-pipeline.sh ./export/ ./discord.sqlite
```

This runs: Export → SQLite → Regex Filter → Haiku Eval → Mark Safe

### Safety Statuses

| Status | Meaning | Used by Agent? |
|--------|---------|----------------|
| `pending` | Not evaluated | ❌ No |
| `regex_flagged` | Matched pattern | ❌ No |
| `flagged` | Haiku risk ≥0.6 | ❌ No |
| `safe` | Passed all checks | ✅ Yes |

---

## Step 3: Ingest to SQLite

Convert JSON to a rich SQLite database:

```bash
python scripts/ingest_rich.py --input ./export/ --output ./discord.sqlite
```

**What gets captured:**
- Every message with full content
- Reactions (individual emoji counts: 🔥 x5, 👍 x12)
- Author roles and colors
- Channel categories and topics
- Reply threading
- Mentions, attachments, embeds

## Step 4: Create Agent Workspace

```bash
mkdir -p ./my-agent/memory
```

Copy template files from `templates/`:
- `SOUL.md` — Community identity (grows through simulation)
- `MEMORY.md` — Long-term milestones
- `LEARNINGS.md` — Patterns discovered
- `AGENTS.md` — Key figures
- `TOOLS.md` — Channels and rituals
- `HEARTBEAT.md` — Maintenance protocol

## Step 5: Generate Daily Memory Files

```bash
python scripts/generate_daily_memory.py --all \
  --db ./discord.sqlite \
  --out ./my-agent/memory/
```

Each day becomes a markdown file with:
- Full conversation logs
- Who said what, when
- Reactions on each message
- New channels/roles that appeared

## Step 6: Simulate Growth (The Soul Emerges)

**This is the key insight:** Process days chronologically.

The agent "lives through" each day, updating its soul files as patterns emerge.

```bash
python scripts/simulate_growth.py --agent ./my-agent/
```

For each day (in order!):
1. Read the day's memory file
2. Update SOUL.md if identity shifted
3. Add to LEARNINGS.md if patterns discovered
4. Record milestones in MEMORY.md
5. Note key figures in AGENTS.md

**Run the prompts with an LLM:**
```bash
# Example with OpenClaw
for f in ./my-agent/simulation/day-*.txt; do
  echo "Processing $f..."
  cat "$f" | openclaw chat --agent my-agent
done
```

## Step 7: Birth the Agent

**Add to OpenClaw config:**

```json
{
  "id": "my-community",
  "workspace": "/path/to/my-agent",
  "memorySearch": {
    "enabled": true,
    "sources": ["memory"]
  },
  "identity": {
    "name": "MyCommunity",
    "emoji": "🔧"
  },
  "heartbeat": {
    "every": "6h",
    "model": "anthropic/claude-sonnet-4-5"
  }
}
```

**Add binding** (Telegram example):
```json
{
  "agentId": "my-community",
  "match": {
    "channel": "telegram",
    "peer": {"kind": "group", "id": "-100XXX:topic:TOPIC_ID"}
  }
}
```

**Restart:** `openclaw gateway restart`

## Step 8: Keep It Alive

Set up a cron job to update daily:

```bash
./scripts/update_agent.sh \
  --agent ./my-agent \
  --db ./discord.sqlite \
  --guild YOUR_GUILD_ID
```

This:
1. Exports new messages since last run
2. Merges into SQLite
3. Regenerates today's memory file
4. Wakes the agent

---

# What the Agent Can Do

Once birthed, your agent can:

**Answer questions:**
- "What were we talking about last week?"
- "Who's the expert on X topic?"
- "What's our stance on Y?"

**Remember culture:**
- Inside jokes and memes
- Community values and norms
- Who helps whom

**Track patterns:**
- Active times and channels
- Emerging topics
- Key contributors

---

# Scripts

## Agent Creation

| Script | Purpose |
|--------|---------|
| `create_agent.sh` | Full pipeline: export → agent |
| `ingest_rich.py` | JSON → SQLite with reactions/roles |
| `generate_daily_memory.py` | SQLite → daily markdown |
| `simulate_growth.py` | Generate soul emergence prompts |
| `incremental_export.sh` | Fetch new messages only |
| `update_agent.sh` | Daily cron: export → memory → wake |

## Security

| Script | Purpose |
|--------|---------|
| `regex-filter.py` | Fast pattern matching for injection attempts |
| `evaluate-safety.py` | Haiku-based semantic safety evaluation |
| `secure-pipeline.sh` | Full security pipeline wrapper |

---

# Environment Variables

| Variable | Description |
|----------|-------------|
| `DISCORD_GUILD_ID` | Your Discord server ID |
| `DISCORD_SOUL_DB` | Path to SQLite database |
| `DISCORD_SOUL_AGENT` | Path to agent workspace |
| `DISCORD_TOKEN_FILE` | Token file (default: ~/.config/discord-exporter-token) |

---

# Troubleshooting

**"No messages in database"**
- Check export directory has .json files
- Verify token has guild access

**"Memory files are empty"**
- SQLite might have dates in wrong format
- Run: `sqlite3 discord.sqlite "SELECT MIN(timestamp), MAX(timestamp) FROM messages"`

**"Agent doesn't remember things"**
- Check `memorySearch.enabled: true` in config
- Verify memory files are in the workspace

**"Simulation prompts seem confused"**
- Process days IN ORDER — don't skip
- Let identity emerge, don't force it

---

*Your Discord has a soul. This skill helps you find it.*
