# ClawHub Listing — DeadClaw

## Metadata

- **Slug**: `deadclaw`
- **Install command**: `openclaw skill install deadclaw`
- **Version**: 1.0.0
- **Author**: Kintupercy
- **License**: MIT
- **Tags**: `security`, `kill-switch`, `emergency`, `agent-safety`, `watchdog`
- **Category**: Security & Safety

---

## Short Description (140 characters)

Emergency kill switch for OpenClaw agents. One message, one button, or one phone tap — everything stops. Includes auto-kill watchdog.

---

## Long Description

### DeadClaw — Emergency Kill Switch

**One tap. Everything stops.**

DeadClaw is a single-purpose emergency kill switch for OpenClaw agents. When something goes wrong — a runaway loop, suspicious behavior, unexpected token burn — DeadClaw halts all running agents instantly. No terminal required. No technical knowledge needed.

Built in response to the ClawHavoc attack (February 2026), which exposed 1,184 malicious skills in the OpenClaw ecosystem. If you run agents autonomously, you need a reliable way to stop everything from wherever you are.

**Three activation methods:**

- **Message trigger** — Send "kill" to any connected channel (Telegram, WhatsApp, Discord, Slack). Works from your phone, anywhere in the world.
- **WebChat button** — A persistent red kill button in your OpenClaw dashboard. One click.
- **Phone shortcut** — A home screen button on iOS or Android. One tap from your lock screen.

All three methods execute the same kill sequence: terminate all agent processes, back up and pause all cron jobs, kill all active sessions, and write a detailed incident log.

**Watchdog (automatic protection):**

DeadClaw includes a background monitor that auto-kills agents when it detects: runaway loops (30min+), excessive token spend (50k tokens in 10min), unauthorized network calls, or file writes outside your workspace. All thresholds are configurable.

**After the kill:**

Send "status" to see what's running. Send "restore" to bring agents back online from the most recent backup. Every script supports --dry-run for safe testing.

**Key features:**

- Idempotent kill script — safe to trigger twice
- Crontab backup before every clear
- Cross-platform (macOS + Linux)
- Works across Telegram, WhatsApp, Discord, Slack
- Step-by-step phone setup guides for non-technical users
- Incident logging with full process details

---

## Screenshots

<!-- REPLACE_THIS: Add screenshots of the WebChat button and phone home screen shortcut -->

1. `screenshot-webchat-button.png` — The red kill button in the WebChat dashboard
2. `screenshot-iphone-homescreen.png` — DeadClaw shortcut on an iPhone home screen
3. `screenshot-kill-confirmation.png` — Telegram confirmation after a kill
4. `screenshot-status-report.png` — Status report in a messaging channel

---

## Install

```bash
openclaw skill install deadclaw
```

---

## Requirements

- OpenClaw v2.0+
- Bash 4.0+
- At least one connected messaging channel (Telegram, WhatsApp, Discord, or Slack) for message triggers
- Optional: OpenClaw WebChat for the dashboard button
- Optional: iOS Shortcuts or Android Tasker/HTTP Shortcuts for the phone shortcut
