---
name: claw-roam
description: Sync OpenClaw workspace between multiple machines (local Mac and remote VPS) via Git. Enables seamless migration of OpenClaw personality, memory, and skills. Use when user wants to (1) push workspace changes to remote before shutdown, (2) pull latest workspace on a new machine, (3) check sync status between machines, (4) migrate OpenClaw to another machine.
---

# Claw Roam - OpenClaw Workspace Sync

Sync your OpenClaw workspace across machines via Git. This allows you to:
- Work on local Mac as primary, seamlessly switch to VPS when traveling
- Maintain continuous memory and personality across different machines
- Backup your OpenClaw state to remote Git repository

## Quick Start

Recommended branch model for multi-device:
- `main` = shared baseline
- `remote` = this server
- `local` = your laptop/desktop

```bash
# Check status (current branch)
claw-roam status

# One-command full sync (recommended)
claw-roam sync

# Or step by step:
# Commit+push current branch
claw-roam push "msg"

# Pull latest for current branch
claw-roam pull

# (Optional) merge another device branch into current branch
claw-roam merge-from local
claw-roam merge-from remote
```

## Commands

### push
Commit and push workspace to remote Git repository.

```bash
claw-roam push [message]
```

- If no message provided, uses timestamp as default
- Automatically adds all changes (git add -A)
- Skips push if no changes detected

### pull
Pull latest workspace from remote and sync.

```bash
claw-roam pull
```

- Fetches latest changes from remote
- Applies changes to current workspace
- Stops and restarts OpenClaw gateway to apply changes (VPS mode)

### status
Check sync status between local and remote.

```bash
claw-roam status
```

- Shows current branch and commit
- Shows unpushed commits (if any)
- Shows uncommitted changes
- Suggests next action

### sync (One-Command Full Sync)

```bash
claw-roam sync
```

Performs the complete sync workflow in one command:

1. **Commit and push current branch** - Saves your local changes
2. **Merge main into current branch** - Gets latest from shared main
3. **Push to main branch** - Shares your changes with other machines

**Workflow diagram:**
```
┌─────────────┐     commit+push     ┌─────────────┐
│ local       │ ───────────────────▶│ origin/local│
│ 分支        │                     │             │
└──────┬──────┘                     └─────────────┘
       │
       │ merge main
       ▼
┌─────────────┐     merge+push      ┌─────────────┐
│ local       │ ───────────────────▶│ main        │
│ 分支        │                     │ (shared)    │
└─────────────┘                     └──────┬──────┘
                                           │
                    ┌──────────────────────┘
                    │ pull
                    ▼
            ┌─────────────┐
            │ remote      │
            │ 分支        │
            └─────────────┘
```

**Recommended daily workflow:**
```bash
# On each machine, just run:
claw-roam sync
```

This ensures:
- Your changes are saved to your branch
- You get latest changes from other machines (via main)
- Other machines can get your changes (via main)

## Setup

1. **Initialize Git repo in workspace** (if not already done):
```bash
cd ~/.openclaw/workspace
git init
git remote add origin <your-repo-url>
```

2. **Create initial commit**:
```bash
git add -A
git commit -m "initial"
git push -u origin main
```

3. **On VPS machine** - clone the repo:
```bash
cd ~
git clone <your-repo-url> openclaw-workspace
ln -s openclaw-workspace ~/.openclaw/workspace
```

## Branch Workflow (Recommended)

For multiple machines, use this branch strategy:

```
local (Mac) ──┐
              ├──► main (shared) ◄── merge & push
remote (VPS) ─┘
```

### Setup Each Machine

**Local Mac:**
```bash
cd ~/.openclaw/workspace
git checkout -b local
git push -u origin local
```

**Remote VPS:**
```bash
cd ~/.openclaw/workspace
git checkout -b remote
git push -u origin remote
```

### Daily Workflow

**On each machine:**

1. **Get latest from main** (获取其他机器的最新内容):
```bash
claw-roam merge-from main
```

2. **Work normally**, then push your changes:
```bash
claw-roam push "update memory"
```

3. **Share to main** (让其他机器能获取):
```bash
git checkout main
git merge local -m "merge: local -> main"
git push origin main
git checkout local
```

### Quick Sync (One-liner)

```bash
# Pull from main, then push to main
claw-roam merge-from main && git checkout main && git merge local && git push && git checkout local
```

### Conflict Resolution

If `merge-from main` has conflicts:
```bash
# Keep your version
git checkout --ours <conflicted-file>
git add -A && git commit -m "merge: resolved conflicts"

# Or keep main's version
git checkout --theirs <conflicted-file>
git add -A && git commit -m "merge: resolved conflicts"
```

## Simple Workflow: Local Primary + VPS Backup

For simpler setups without branches:

### Daily Usage (Local Mac)
Just use OpenClaw normally. Before shutdown:

```bash
claw-roam push "end of day sync"
```

Or let it auto-push via cron:
```bash
# Add to crontab
*/10 * * * * cd ~/.openclaw/workspace && git add -A && git commit -m "auto: $(date)" && git push
```

### Switching to VPS
1. Ensure local has pushed: `claw-roam push`
2. On VPS: `claw-roam pull`
3. Update Telegram webhook to point to VPS (if using webhook mode)
4. Continue using alternative bot token on VPS

### Returning to Local
1. On VPS: `claw-roam push`
2. On local: `claw-roam pull`
3. Update Telegram webhook back to local (if needed)

## What Gets Synced

**Synced (preserved across machines):**
- `SOUL.md` - Your agent's personality
- `MEMORY.md` - Long-term memory
- `memory/*.md` - Daily conversation logs
- `skills/` - All installed skills
- `AGENTS.md`, `USER.md` - Context files
- `TOOLS.md` - Device configurations
- `HEARTBEAT.md` - Periodic tasks

**Not Synced (machine-specific):**
- Session database (SQLite) - But this is rebuilt from memory files
- Gateway runtime state
- Platform-specific paths in configs

## Troubleshooting

### "Repository not found"
Run setup steps above to initialize Git repository.

### "Merge conflicts"
If you edited on both machines without syncing:
```bash
# On the machine with changes you want to keep
git pull --strategy=ours
git push
```

### "Permission denied"
Ensure your Git remote is configured with proper authentication (SSH key or token).

## Scripts

Use bundled scripts directly:
```bash
~/.openclaw/workspace/skills/claw-roam/scripts/claw-roam.sh push
~/.openclaw/workspace/skills/claw-roam/scripts/claw-roam.sh pull
~/.openclaw/workspace/skills/claw-roam/scripts/claw-roam.sh status
```
