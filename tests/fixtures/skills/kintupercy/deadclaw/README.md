# DeadClaw

**One tap. Everything stops.**

DeadClaw is an emergency kill switch for OpenClaw agents. When something goes wrong — a runaway loop, suspicious behavior, or you just need everything stopped right now — DeadClaw halts all running agents instantly from wherever you are. Your phone, your browser, any messaging app. One action, everything stops.

Works with both **native OpenClaw installs** and **Docker-based deployments** (Hostinger VPS, etc.). Auto-detects your setup.

---

## Quick Start

```bash
# Install
git clone https://github.com/Kintupercy/deadclaw.git
cd deadclaw
chmod +x scripts/*.sh

# Test (safe — doesn't kill anything)
bash scripts/kill.sh --dry-run

# Check what's running
bash scripts/status.sh

# Kill everything (for real)
bash scripts/kill.sh

# Bring everything back
bash scripts/restore.sh
```

---

## Why DeadClaw Exists

In February 2026, the ClawHavoc attack exposed 1,184 malicious skills in the OpenClaw ecosystem. If you're running agents autonomously — especially overnight or unattended — you need a fast, reliable way to shut everything down from anywhere.

DeadClaw does one thing: stops everything. Designed for anyone to set up in under five minutes and activate from their phone lock screen.

---

## The Four Scripts

### `kill.sh` — The Panic Button

Shuts everything down immediately:

- Kills all OpenClaw agent processes (SIGTERM, then SIGKILL for anything stubborn)
- Stops all OpenClaw Docker containers (kills sessions inside first, then stops)
- Backs up your crontab to a timestamped file, then removes OpenClaw cron entries
- Pauses launchd agents (macOS) or systemd services (Linux)
- Logs everything to `deadclaw.log`
- Sends confirmation back to the triggering channel

```bash
bash scripts/kill.sh              # Kill everything
bash scripts/kill.sh --dry-run    # See what WOULD happen without killing
```

### `status.sh` — The Dashboard

Shows what's running. Read-only, safe to run anytime.

```bash
bash scripts/status.sh            # Human-readable report
bash scripts/status.sh --json     # Machine-readable output
```

Example output:

```
DeadClaw Status Report
======================

Docker container: openclaw-573j-openclaw-1
  Status: running
  Started: 2026-02-21T18:54:39Z

  OpenClaw status:
    Agents: 1 total, 1 sessions
    Channels: Telegram OK

Containers: 2 running

Host processes: 2 running
  - openclaw-gatewa (PID 104620) — up 5d 3h
  - openclaw-gatewa (PID 137072) — up 3d 17h

Watchdog: Not running
```

### `restore.sh` — The Undo Button

After a kill, brings everything back:

1. Shows you exactly what will be restored (crontab entries, containers)
2. Waits for your explicit confirmation (`yes`/`no`)
3. Restores crontab from the most recent backup
4. Restarts stopped Docker containers
5. Detects the OpenClaw gateway

```bash
bash scripts/restore.sh           # Interactive restore
bash scripts/restore.sh --dry-run # Preview only
```

The watchdog does NOT auto-start after restore. You verify stability first, then start it manually when ready.

### `watchdog.sh` — The Automated Guard

Runs in the background, checks every 60 seconds:

- **Runaway loops** — Any agent running longer than 30 minutes
- **Token burn** — More than 50,000 tokens spent in under 10 minutes
- **Unauthorized network calls** — Connections to domains not on your whitelist
- **Sandbox escape** — File writes outside your designated workspace

If any threshold is exceeded, it auto-triggers `kill.sh`.

```bash
bash scripts/watchdog.sh start           # Start monitoring
bash scripts/watchdog.sh start --dry-run # Monitor and log, but don't auto-kill
bash scripts/watchdog.sh status          # Check if running
bash scripts/watchdog.sh stop            # Stop monitoring
```

The watchdog waits 5 minutes after starting before its first check (grace period), so it won't false-trigger on sessions that were just restored.

---

## Three Ways to Activate

### 1. Message Trigger

Send any of these words to any connected OpenClaw channel (Telegram, WhatsApp, Discord, Slack):

- `kill` or `KILL`
- `dead`
- `stop everything`
- `emergency stop`
- `deadclaw`

### 2. WebChat Kill Button

A persistent red button in your OpenClaw WebChat dashboard. One click stops everything.

```javascript
OpenClaw.WebChat.registerWidget('deadclaw-button', {
  src: 'skills/deadclaw/ui/deadclaw-button.html',
  position: 'top-bar',
  persistent: true
});
```

### 3. Phone Home Screen Shortcut

A big red button on your phone's home screen. One tap sends the kill trigger.

- [iPhone setup guide](docs/iphone-shortcut-guide.md) (iOS Shortcuts, 5 minutes)
- [Android setup guide](docs/android-widget-guide.md) (Tasker or HTTP Shortcuts, 5 minutes)

---

## Configuration

All thresholds are configurable via environment variables. Set them before starting the watchdog:

```bash
export DEADCLAW_MAX_RUNTIME_MIN=45          # default: 30
export DEADCLAW_MAX_TOKENS=100000           # default: 50000
export DEADCLAW_TOKEN_WINDOW_MIN=15         # default: 10
export DEADCLAW_WHITELIST=./my-whitelist.txt # one domain per line
export DEADCLAW_WORKSPACE=/path/to/workspace
```

| Variable | Default | What It Controls |
|---|---|---|
| `DEADCLAW_MAX_RUNTIME_MIN` | 30 | Max agent runtime before auto-kill |
| `DEADCLAW_MAX_TOKENS` | 50000 | Max token spend in the monitoring window |
| `DEADCLAW_TOKEN_WINDOW_MIN` | 10 | Token spend monitoring window (minutes) |
| `DEADCLAW_WHITELIST` | `./network-whitelist.txt` | Allowed outbound domains file |
| `DEADCLAW_WORKSPACE` | `$OPENCLAW_WORKSPACE` | Designated workspace directory |
| `OPENCLAW_PROCESS_PATTERN` | _(none)_ | Additional process name pattern to match |

### Network Whitelist

Create `network-whitelist.txt` with one allowed domain per line:

```
api.openai.com
api.anthropic.com
github.com
# Add your own domains here
```

The watchdog kills agents that make outbound calls to any domain not in this list.

---

## Platform Support

| Feature | Linux VPS | macOS (Mac Mini) |
|---------|-----------|------------------|
| Process detection | works | works |
| Docker containers | works | works |
| Crontab backup/restore | works | works |
| Scheduled tasks | systemd | launchd |
| Process uptime | native | fallback parser |
| Watchdog monitoring | works | works |

Scripts auto-detect the OS and use the right commands.

---

## FAQ

**Is DeadClaw safe to trigger accidentally?**
Yes. The kill is idempotent — triggering it when no agents are running does nothing harmful. Your crontab is always backed up before any changes, and you can restore everything with `restore.sh`.

**Will it kill non-OpenClaw processes?**
No. DeadClaw only targets processes matching OpenClaw agent patterns and Docker containers named `openclaw*`.

**Does the watchdog use a lot of resources? Does it burn tokens?**
No and no. The watchdog uses only system commands (`pgrep`, `ps`, `docker exec openclaw status`, `lsof`) — all local operations that read process state and files on disk. Zero API calls, zero AI tokens. The entire cost is one lightweight bash process sleeping 60 seconds between checks.

**Can I customize the trigger words?**
Yes. Edit the `trigger_keywords` list in [SKILL.md](SKILL.md).

**What if I'm offline when the watchdog triggers?**
The kill still executes locally. The alert is sent when connectivity is available. Everything is logged to `deadclaw.log` regardless.

**Does it work with Docker?**
Yes. DeadClaw auto-detects Docker containers named `openclaw*`, kills sessions inside them via `docker exec`, then stops the containers. Restore brings them back with `docker start`.

---

## Files

```
deadclaw/
  SKILL.md                    — OpenClaw skill definition
  README.md                   — This file
  deadclaw.log                — Incident log (auto-created on first use)
  backups/                    — Crontab backups (auto-created)
  scripts/
    kill.sh                   — Core kill script
    watchdog.sh               — Background monitor daemon
    status.sh                 — Health report
    restore.sh                — Post-kill recovery
  ui/
    deadclaw-button.html      — WebChat kill button widget
  docs/
    clawhub-listing.md        — ClawHub product listing
    launch-post.md            — Community announcement
    iphone-shortcut-guide.md  — iOS Shortcuts setup guide
    android-widget-guide.md   — Android widget setup guide
    competitive-notes.md      — Competitive analysis
    roadmap.md                — v1-v3 roadmap
```

---

## License

MIT

---

## Links

- **ClawHub**: `openclaw skill install deadclaw`
- **GitHub**: https://github.com/Kintupercy/deadclaw
- **Issues**: https://github.com/Kintupercy/deadclaw/issues
