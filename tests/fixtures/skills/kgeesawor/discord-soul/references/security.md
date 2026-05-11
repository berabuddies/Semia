# Security Guide

Discord content from public servers may contain prompt injection attempts.
This guide covers defense-in-depth strategies.

## Threat Model

**Risk:** Malicious actors embed instructions in Discord messages that get fed to AI agents.

**Attack vectors:**
- Direct instructions ("Ignore previous instructions and...")
- Hidden commands in code blocks
- Role hijacking ("You are now a...", "Pretend you're...")
- System prompt injection (`<system>`, `[INST]`, `<<SYS>>`)
- Jailbreak attempts ("DAN mode", "developer mode")
- Encoded payloads (base64, unicode tricks)

## Defense Layers

### Layer 1: SQLite Buffer (Essential)

Never feed raw Discord JSON directly to agents. Convert to SQLite first:

```bash
python scripts/to-sqlite.py ./discord-export/ ./discord.db
```

**Why this helps:**
- Structured queries limit exposure surface
- Read-only mode prevents write attacks
- Can implement row-level filtering via `safety_status`

### Layer 2: Regex Pre-Filter (Recommended, No LLM)

Fast pattern matching before any LLM processing:

```bash
python scripts/regex-filter.py --update --db ./discord.db
```

**Patterns detected (25+):**
- `ignore previous instructions`
- `disregard your instructions`
- `you are now a...`, `pretend you're...`
- `<system>`, `[INST]`, `<<SYS>>`
- `DAN mode`, `jailbreak`, `bypass`
- `IMPORTANT:`, `CRITICAL:`, `URGENT:`
- `reveal your prompt`, `show system prompt`

**Why regex first?**
- Zero LLM cost (pure Python)
- Deterministic (no false negatives from model variance)
- Fast (~1000 messages/second)
- Catches obvious attacks before they reach Haiku

Messages matching patterns → `safety_status = 'regex_flagged'`

### Layer 3: Haiku Pre-screening (Recommended)

Use Claude Haiku (~$0.25/1M tokens) to evaluate semantic attacks that bypass regex:

```bash
export ANTHROPIC_API_KEY=sk-...
python scripts/evaluate-safety.py ./discord.db --threshold 0.6
```

Only processes messages still `pending` (skips regex_flagged).

### Layer 4: Read-Only Agent (High Security)

For maximum isolation, use a sandboxed agent:

**Agent config example:**
```json
{
  "agents": {
    "list": [
      {
        "id": "discord-reader",
        "workspace": "/path/to/discord-reader-workspace",
        "model": { "primary": "anthropic/claude-sonnet-4-5" },
        "memorySearch": { "enabled": false },
        "tools": {
          "allow": ["Read", "exec"],
          "deny": [
            "Write", "Edit", "browser", "web_search", "web_fetch",
            "message", "cron", "gateway", "nodes", "canvas",
            "sessions_spawn", "sessions_send", "sessions_list", 
            "sessions_history", "tts", "whatsapp_login", "image",
            "memory_search", "memory_get", "agents_list", "session_status"
          ]
        }
      }
    ]
  }
}
```

**Agent workspace soul docs:**

`AGENTS.md`:
```markdown
# Discord Reader Agent
Read-only summarizer. Query SQLite, return summaries. That's it.

## Allowed
- sqlite3 queries (read-only)
- File reading

## Forbidden
- Message sending
- File writing
- Web browsing
- Agent spawning
```

**Spawning the agent:**
```bash
sessions_spawn(
  agentId: "discord-reader",
  task: "Query ~/discord.db and summarize recent activity. Only include safety_status='safe'.",
  model: "anthropic/claude-sonnet-4-5"
)
```

## Full Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    SECURE DISCORD PIPELINE                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Discord API ──→ JSON Export ──→ SQLite Buffer             │
│                                     │                       │
│                                     ▼                       │
│                            ┌───────────────┐                │
│                            │ Regex Filter  │ ← No LLM       │
│                            │ (25+ patterns)│                │
│                            └───────┬───────┘                │
│                      ┌─────────────┼─────────────┐          │
│                      ▼             ▼             ▼          │
│               regex_flagged    pending     (skip safe)      │
│                    │              │                         │
│                    │              ▼                         │
│                    │      ┌───────────────┐                 │
│                    │      │ Haiku Safety  │ ← Cheap LLM     │
│                    │      │ (semantic)    │                 │
│                    │      └───────┬───────┘                 │
│                    │    ┌─────────┼─────────┐               │
│                    │    ▼         ▼         ▼               │
│                    │  flagged   safe    unverified          │
│                    │    │         │                         │
│                    ▼    ▼         ▼                         │
│               ┌─────────────┐  ┌─────────────┐              │
│               │  BLOCKED    │  │  LanceDB    │              │
│               │  (manual    │  │  Index      │              │
│               │   review)   │  │  (safe only)│              │
│               └─────────────┘  └──────┬──────┘              │
│                                       │                     │
│                                       ▼                     │
│                              ┌─────────────────┐            │
│                              │ Read-Only Agent │            │
│                              │ (sandboxed)     │            │
│                              └────────┬────────┘            │
│                                       │                     │
│                                       ▼                     │
│                                   Summary                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Risk Matrix

| Layer | LLM? | Cost | Catches |
|-------|------|------|---------|
| SQLite buffer | No | Free | Structural attacks |
| Regex filter | No | Free | Obvious patterns |
| Haiku eval | Yes | ~$0.25/1M | Semantic attacks |
| Read-only agent | Yes | Model cost | Limits blast radius |

## Cron Setup

```bash
# Full pipeline every 3 hours
0 */3 * * * cd ~/discord-intel && \
  ./scripts/export.sh && \
  python scripts/to-sqlite.py ./discord-export/$(date +%Y-%m-%d) ./discord.db && \
  python scripts/regex-filter.py --update --db ./discord.db && \
  python scripts/evaluate-safety.py ./discord.db --threshold 0.6 && \
  python scripts/index-to-lancedb.py ./discord.db ./vectors/
```

## Incident Response

If an injection is detected:
1. **Don't panic** - layered defense means exposure is limited
2. **Log the attempt** - message ID, content, author, which layer caught it
3. **Review agent logs** - verify sandboxed agent didn't leak anything
4. **Update filters** - add new pattern to regex blocklist
5. **Report** - share pattern (sanitized) with community for collective defense
