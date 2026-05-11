---
name: deadclaw
description: >
  Emergency kill switch for OpenClaw agents. Instantly halts all running agents,
  pauses scheduled jobs, kills active sessions, and logs everything — triggered by
  a single message, a WebChat button, or a phone home screen shortcut. Includes a
  background watchdog that auto-kills agents on runaway loops, excessive token spend,
  unauthorized network calls, or out-of-bounds file writes. Use this skill whenever
  the user mentions: emergency stop, kill switch, stop agents, halt agents, panic
  button, deadclaw, agent safety, runaway agent, kill all, stop everything, or any
  urgent need to shut down OpenClaw processes immediately.
version: 1.0.0
author: "Kintupercy"
trigger_keywords:
  - kill
  - KILL
  - dead
  - deadclaw
  - stop everything
  - emergency stop
  - "🔴"
  - status
  - restore
allowed-tools:
  - bash
  - messaging
  - webchat
---

# DeadClaw — Emergency Kill Switch for OpenClaw Agents

> "One tap. Everything stops."

DeadClaw is a single-purpose emergency kill switch. When triggered, it immediately
halts all running OpenClaw agent processes, stops Docker containers, pauses all
scheduled cron jobs and heartbeats, kills all active sessions, and writes a
timestamped incident log. It then confirms back to whichever surface triggered it.

Works with both **native OpenClaw installs** and **Docker-based deployments**
(Hostinger VPS, etc.). Auto-detects your setup.

## Why DeadClaw Exists

The ClawHavoc attack (February 2026) exposed 1,184 malicious skills in the OpenClaw
ecosystem. People run agents autonomously — often overnight, often unattended. When
something goes wrong, you need a way to stop everything from wherever you are, even
from your phone. DeadClaw is that way.

---

## Activation Methods

DeadClaw supports three activation methods. All three execute the exact same kill
sequence — the only difference is how the user triggers it.

### Method 1: Message Trigger

The user sends a trigger word to any connected OpenClaw channel (Telegram, WhatsApp,
Discord, Slack, or any other connected channel). The following words activate DeadClaw:

- `kill` or `KILL`
- `dead`
- `stop everything`
- `emergency stop`
- `deadclaw`
- `🔴`

When a trigger word is detected:

1. Execute `scripts/kill.sh` from the DeadClaw skill directory
2. Capture the output (process count, containers stopped, cron jobs paused, timestamp)
3. Send confirmation back to the **same channel** the trigger came from:
   `🔴 DeadClaw activated. All agents stopped. [timestamp] — [X] killed ([X] processes, [X] containers). [X] cron jobs paused. See deadclaw.log for full report.`

### Method 2: WebChat Kill Button

A persistent red button rendered in the OpenClaw WebChat dashboard. The HTML widget
is located at `ui/deadclaw-button.html`. It calls `kill.sh` via OpenClaw's WebChat
API hooks (`window.OpenClaw.exec()`). If the WebChat hooks are unavailable, the
button degrades to showing an error message with manual instructions.

To embed the button, use OpenClaw's WebChat customization hooks:

```javascript
OpenClaw.WebChat.registerWidget('deadclaw-button', {
  src: 'skills/deadclaw/ui/deadclaw-button.html',
  position: 'top-bar',
  persistent: true
});
```

### Method 3: Phone Home Screen Shortcut

A pre-built shortcut that sends the kill trigger message (`deadclaw`) to the user's
configured Telegram bot. Setup guides for iOS and Android are in `docs/`:

- `docs/iphone-shortcut-guide.md` — iOS Shortcuts setup
- `docs/android-widget-guide.md` — Android widget setup (Tasker or HTTP Shortcuts)

---

## Watchdog (Passive Protection)

DeadClaw includes a background watchdog (`scripts/watchdog.sh`) that monitors for
dangerous conditions and auto-triggers the kill without any user action.

The watchdog checks every 60 seconds for (after a 5-minute startup grace period):

1. **Runaway loops** — Any agent process or Docker session running longer than 30 minutes
2. **Token burn** — Token spend exceeding 50,000 tokens in under 10 minutes
3. **Unauthorized network** — Outbound network calls to domains not on the user's whitelist
4. **Sandbox escape** — Any process attempting to write outside the designated OpenClaw workspace

The watchdog uses zero AI tokens — all checks use local system commands only.

When the watchdog auto-triggers, it sends an alert explaining the reason:
`🔴 DeadClaw auto-triggered. Reason: [specific reason]. All processes stopped. Check deadclaw.log.`

### Watchdog Configuration

The watchdog reads its thresholds from environment variables (with sensible defaults):

| Variable | Default | Description |
|---|---|---|
| `DEADCLAW_MAX_RUNTIME_MIN` | 30 | Max agent runtime in minutes before auto-kill |
| `DEADCLAW_MAX_TOKENS` | 50000 | Max token spend in the monitoring window |
| `DEADCLAW_TOKEN_WINDOW_MIN` | 10 | Token spend monitoring window in minutes |
| `DEADCLAW_WHITELIST` | `./network-whitelist.txt` | Allowed outbound domains (one per line) |
| `DEADCLAW_WORKSPACE` | `$OPENCLAW_WORKSPACE` | Designated workspace directory |

Start the watchdog:

```bash
scripts/watchdog.sh start
```

Stop the watchdog:

```bash
scripts/watchdog.sh stop
```

---

## Additional Commands

### Status Check

User sends `status` to any connected channel. DeadClaw responds with a plain-English
health report by executing `scripts/status.sh`:

- What agents are currently running (name, PID, uptime)
- Current token spend rate
- Whether the watchdog is active
- Any warnings about approaching thresholds

### Restore After Kill

User sends `restore` to any connected channel. DeadClaw executes `scripts/restore.sh`,
which:

1. Shows what will be restored (backed-up crontab entries, stopped Docker containers, disabled services)
2. Prompts: "Restore [X] cron jobs from backup taken at [timestamp]? (yes/no)"
3. Restores the crontab from the most recent backup
4. Restarts stopped OpenClaw Docker containers
5. Detects the OpenClaw gateway
6. Confirms restoration with a summary

The watchdog does NOT auto-start after restore — the user verifies stability first,
then starts it manually with `scripts/watchdog.sh start`.

---

## Scripts Reference

| Script | Purpose |
|---|---|
| `scripts/kill.sh` | Core kill script — stops all agents + Docker containers, pauses cron, logs incident |
| `scripts/watchdog.sh` | Background monitor daemon — auto-triggers kill on threshold breach |
| `scripts/status.sh` | Health report — shows running agents, Docker containers, token spend, watchdog status |
| `scripts/restore.sh` | Post-kill recovery — restores crontab, restarts Docker containers |

All scripts support a `--dry-run` flag that logs what would happen without taking action.

---

## Incident Log

All kill events are logged to `deadclaw.log` in the skill directory. Each entry
records: timestamp, trigger source (channel name), trigger method (message/button/
watchdog/auto), processes killed (count and PIDs), Docker containers stopped, cron
jobs paused, and token spend at time of kill. The log is append-only and never
automatically cleared.

---

## Platform Support

DeadClaw works on both **Linux** (VPS, bare metal) and **macOS** (Mac Mini, MacBook).
Scripts auto-detect the OS and use the appropriate commands:

- **Linux**: `systemctl` for services, `pgrep` for processes, Docker support
- **macOS**: `launchctl` for agents, `pgrep` for processes, Docker support
