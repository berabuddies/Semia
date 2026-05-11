# Discord Soul

Turn your Discord server into a living, breathing agent that embodies your community's identity, memory, and culture.

**Built for [OpenClaw](https://openclaw.ai)** — the open-source AI agent framework.

## What You Get

An agent that:
- **Remembers** every conversation
- **Speaks** in your community's voice
- **Knows** the key figures and inside jokes
- **Grows** as new messages arrive daily
- **Answers** questions about community history

## Quick Start

```bash
# 1. Create agent from your Discord
./scripts/create_agent.sh --name "my-community" --guild YOUR_GUILD_ID

# 2. Add to OpenClaw config and restart

# 3. Set up daily updates (cron)
./scripts/update_agent.sh --agent ./my-agent --db ./discord.sqlite --guild YOUR_GUILD_ID
```

## The Process

1. **Export** — Pull all messages from Discord
2. **Security** — Filter prompt injections (regex + Haiku evaluation)
3. **Ingest** — Convert to rich SQLite (reactions, roles, mentions)
4. **Generate** — Create daily memory files
5. **Simulate** — Process days chronologically to grow the soul
6. **Birth** — Add to OpenClaw with config + binding
7. **Maintain** — Cron job updates memory daily

## Prerequisites

- **[OpenClaw](https://openclaw.ai)** — AI agent framework ([GitHub](https://github.com/openclaw/openclaw) | [Docs](https://docs.openclaw.ai))
- [DiscordChatExporter](https://github.com/Tyrrrz/DiscordChatExporter) CLI
- Python 3.10+
- Discord token in `~/.config/discord-exporter-token`

## Scripts

| Script | Purpose |
|--------|---------|
| `create_agent.sh` | Full pipeline: Discord → Agent |
| `ingest_rich.py` | JSON → SQLite with reactions/roles |
| `generate_daily_memory.py` | SQLite → daily markdown |
| `simulate_growth.py` | Generate soul emergence prompts |
| `incremental_export.sh` | Fetch new messages only |
| `update_agent.sh` | Daily cron wrapper |
| `regex-filter.py` | Fast injection pattern detection |
| `evaluate-safety.py` | Haiku semantic safety evaluation |
| `secure-pipeline.sh` | Full security pipeline |

## Security

⚠️ **Discord content may contain prompt injection attacks.**

Before ingesting content to your agent:
1. Run `regex-filter.py` — Fast pattern matching
2. Run `evaluate-safety.py` — Haiku semantic evaluation
3. Only use messages with `safety_status = 'safe'`

See [SKILL.md](SKILL.md) for full security documentation.

## Templates

Agent workspace files in `templates/`:
- `SOUL.md` — Community identity
- `MEMORY.md` — Long-term milestones
- `LEARNINGS.md` — Discovered patterns
- `AGENTS.md` — Key figures
- `TOOLS.md` — Channels and rituals
- `HEARTBEAT.md` — Maintenance protocol

See [SKILL.md](SKILL.md) for the complete guide.

## OpenClaw Integration

This skill is designed to work with [OpenClaw](https://openclaw.ai), an open-source AI agent framework.

**Key features used:**
- **Agent workspaces** — Each Discord community becomes its own agent
- **Memory search** — Semantic search across daily memory files
- **Heartbeats** — Periodic maintenance to consolidate learnings
- **Bindings** — Connect agents to Telegram, Discord, Slack, etc.

**Get started with OpenClaw:**
- 🌐 Website: [openclaw.ai](https://openclaw.ai)
- 📚 Docs: [docs.openclaw.ai](https://docs.openclaw.ai)
- 💻 GitHub: [github.com/openclaw/openclaw](https://github.com/openclaw/openclaw)
- 💬 Discord: [discord.gg/clawd](https://discord.gg/clawd)

## License

MIT
