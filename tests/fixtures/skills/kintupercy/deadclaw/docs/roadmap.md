# DeadClaw — Roadmap

---

## v1.0 — Emergency Kill Switch (Current Release)

Everything in this release is about one thing: stopping all agents instantly from anywhere.

**Core kill functionality**:

- Kill all running OpenClaw agent processes (SIGTERM then SIGKILL)
- Back up and clear OpenClaw cron jobs
- Terminate all active agent sessions
- Write timestamped incident log
- Confirm back to triggering channel

**Three activation methods**:

- Message trigger via any connected channel (Telegram, WhatsApp, Discord, Slack)
- WebChat dashboard kill button (HTML widget)
- Phone home screen shortcut (iOS Shortcuts + Android Tasker/HTTP Shortcuts)

**Watchdog (passive protection)**:

- Background daemon monitoring on 60-second intervals
- Auto-kill on: runaway loops (30min+), token burn (50k/10min), unauthorized network calls, sandbox escape
- Configurable thresholds via environment variables
- PID file management for clean start/stop

**Recovery**:

- Status command for health reports
- Restore command with confirmation step
- Crontab backup before every clear

**Developer experience**:

- --dry-run flag on all scripts
- Idempotent kill (safe to trigger twice)
- Cross-platform support (macOS + Linux)
- Clear comments throughout all scripts

---

## v2.0 — Proactive Breach Detection

v2 shifts from reactive (stop things after they go wrong) to proactive (detect threats before a kill is needed). The watchdog evolves from a threshold monitor into an intelligent threat detection system.

**Planned features**:

- **Behavioral analysis**: Learn normal agent patterns (typical runtime, token spend curves, network call frequency) and alert on deviations. Rather than fixed thresholds, detect when agents are behaving abnormally for their specific workload.

- **Real-time alerts without killing**: New alert tier between "everything's fine" and "kill everything." Warnings sent to your phone when an agent approaches a threshold, giving you time to investigate before the watchdog auto-kills. Configurable alert channels separate from kill triggers.

- **Skill reputation scoring**: Cross-reference installed skills against ClawHub's community reports and known-malicious skill signatures. Flag agents running skills with low reputation scores or recently reported vulnerabilities.

- **Network traffic analysis**: Move beyond domain whitelisting to actual traffic pattern analysis. Detect data exfiltration attempts (large outbound payloads), command-and-control communication patterns, and encrypted connections to unusual endpoints.

- **File integrity monitoring**: Track which files agents modify and flag unexpected changes to system files, credentials, SSH keys, or other sensitive paths — even within the allowed workspace.

- **Incident replay**: Record agent activity (process state snapshots, network logs, file changes) so that after a kill, you can replay exactly what the agent was doing. Helps answer "what happened?" not just "something happened."

**Architecture changes**:

- Watchdog rewritten as a lightweight Go binary for better performance and cross-platform consistency
- Persistent state store for behavioral baselines (SQLite)
- Webhook support for alerts (in addition to messaging channels)
- REST API for programmatic access to status and alert data

---

## v3.0 — Companion Mobile App

v3 brings DeadClaw to a native mobile experience. Instead of shortcut workarounds and Telegram bots, a purpose-built app with push notifications and a real-time dashboard.

**Planned features**:

- **Native iOS and Android app**: Purpose-built DeadClaw app with a prominent kill button, agent activity dashboard, and alert history.

- **Push notifications**: Real-time push alerts when the watchdog detects a threat or auto-triggers a kill. No dependency on Telegram or other messaging apps.

- **Agent activity dashboard**: See all running agents, their uptime, token spend, and network activity in real time. Visual indicators for agent health (green/yellow/red).

- **One-tap kill from notification**: When you receive a threat alert, kill all agents directly from the notification without opening the app.

- **Kill history and analytics**: Review past kill events, see patterns (which agents cause the most kills, what times of day, which threat types), and get recommendations for hardening your setup.

- **Multi-environment support**: Monitor and kill agents across multiple machines/servers from a single app. Add environments by scanning a QR code or entering a connection token.

- **Apple Watch / Wear OS complication**: A kill button on your watch face. Tap your wrist, agents stop.

- **Biometric confirmation**: Optional Face ID / fingerprint confirmation before a kill fires, for environments where accidental triggers would be costly.

**Architecture changes**:

- DeadClaw agent component runs alongside the watchdog on each monitored machine
- Secure WebSocket connection between agent and mobile app (end-to-end encrypted)
- Cloud relay service for push notifications (optional — direct connection mode available for privacy-conscious users)
- API gateway for multi-environment management

---

## Beyond v3 — Ideas Under Consideration

These aren't committed to any version. They're ideas we're exploring based on community feedback.

- **Team mode**: Multiple users can kill the same environment. Useful for teams running shared agent infrastructure. Kill events show who triggered them.
- **Scheduled safe hours**: Define time windows when agents are allowed to run autonomously. Outside those windows, the watchdog is extra aggressive.
- **Integration marketplace**: Pre-built integrations with popular monitoring tools (Grafana, Datadog, PagerDuty) for teams that want DeadClaw alerts in their existing dashboards.
- **Agent quarantine**: Instead of killing an agent immediately, isolate it — cut network access and freeze file writes — so you can investigate while it's still running.
- **Community threat feed**: Anonymized, opt-in sharing of watchdog trigger events across DeadClaw users to build a collective threat detection model.
