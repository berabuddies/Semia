# DeadClaw Launch Post — OpenClaw Community (Discord)

---

**Posting to: #announcements or #new-skills**

---

Two weeks ago, the ClawHavoc attack hit the OpenClaw ecosystem. 1,184 malicious skills. Some of them sat quietly in people's environments for weeks before anyone noticed. The community response has been great — the security audit, the new review process, the detection tools.

But there's a gap nobody's filled yet.

When you discover something wrong at 2am on your phone, what do you actually do? SSH into your server? Open a terminal? If you're running agents overnight — and a lot of us are — there's no fast, non-technical way to just stop everything.

That's what DeadClaw does. One action, everything stops.

**Three ways to trigger it:**

**Message trigger.** Send "kill" to any connected OpenClaw channel — Telegram, WhatsApp, Discord, Slack. From your phone, from a friend's phone, from anywhere. DeadClaw detects it, kills all running agents, pauses all cron jobs (after backing up your crontab), and confirms back to that same channel. This is the feature nobody else has built yet.

**WebChat button.** A persistent red kill button in your WebChat dashboard. For when something is going wrong right in front of you. One click.

**Phone home screen shortcut.** A big red button on your phone's home screen. One tap sends the kill trigger to Telegram. Included are step-by-step setup guides for both iOS Shortcuts and Android (Tasker/HTTP Shortcuts). Written for non-technical users, takes under 5 minutes.

All three methods run the exact same kill script.

**There's also a watchdog.** A lightweight background monitor that auto-kills agents if it detects: runaway loops (30min+), excessive token burn (50k tokens in 10min), outbound network calls to domains not on your whitelist, or file writes outside your workspace. You get an alert explaining exactly why it fired. Configurable thresholds.

**After a kill:** send "status" for a health report, send "restore" to bring everything back from the backup. Every script supports `--dry-run` for safe testing.

DeadClaw is not a security suite. It's not trying to replace openclaw-defender or clawsec. It does one thing. It does it from your phone. It works for people who don't use terminals.

Install:
```
openclaw skill install deadclaw
```

GitHub: https://github.com/Kintupercy/deadclaw

If this is useful to you, a star on the repo helps other people find it. If something's broken or missing, open an issue — happy to fix it.

Stay safe out there.
