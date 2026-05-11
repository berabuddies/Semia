#!/bin/bash
# update_agent_memory.sh
# Full update pipeline: export → ingest → generate memory → wake agent
#
# Usage: ./update_agent_memory.sh --agent <workspace> --db <sqlite> --guild <id>
#
# Environment variables (alternative to flags):
#   DISCORD_SOUL_AGENT   Path to agent workspace
#   DISCORD_SOUL_DB      Path to SQLite database
#   DISCORD_GUILD_ID      Discord Guild/Server ID

set -e

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --agent|-a)
            AGENT_WORKSPACE="$2"
            shift 2
            ;;
        --db|-d)
            SQLITE_DB="$2"
            shift 2
            ;;
        --guild|-g)
            GUILD_ID="$2"
            shift 2
            ;;
        --skip-export)
            SKIP_EXPORT=1
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Fallback to environment variables
AGENT_WORKSPACE="${AGENT_WORKSPACE:-$DISCORD_SOUL_AGENT}"
SQLITE_DB="${SQLITE_DB:-$DISCORD_SOUL_DB}"
GUILD_ID="${GUILD_ID:-$DISCORD_GUILD_ID}"
MEMORY_PATH="${DISCORD_SOUL_MEMORY:-$AGENT_WORKSPACE/memory}"

# Validate
if [ -z "$AGENT_WORKSPACE" ]; then
    echo "Error: No agent workspace specified. Use --agent or set DISCORD_SOUL_AGENT"
    exit 1
fi

if [ -z "$SQLITE_DB" ]; then
    echo "Error: No database specified. Use --db or set DISCORD_SOUL_DB"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$AGENT_WORKSPACE/memory-update.log"
TODAY=$(date +%Y-%m-%d)

echo "[$(date)] =====================================" | tee -a "$LOG_FILE"
echo "[$(date)] Starting memory update pipeline" | tee -a "$LOG_FILE"
echo "[$(date)] Agent: $AGENT_WORKSPACE" | tee -a "$LOG_FILE"
echo "[$(date)] Database: $SQLITE_DB" | tee -a "$LOG_FILE"
echo "[$(date)] =====================================" | tee -a "$LOG_FILE"

# Step 1: Run incremental export (if guild ID provided and not skipped)
if [ -z "$SKIP_EXPORT" ] && [ -n "$GUILD_ID" ]; then
    echo "[$(date)] Step 1: Running incremental export..." | tee -a "$LOG_FILE"
    "$SCRIPT_DIR/incremental_export.sh" --guild "$GUILD_ID" --db "$SQLITE_DB" 2>&1 | tee -a "$LOG_FILE"
else
    echo "[$(date)] Step 1: Skipping export (no guild ID or --skip-export)" | tee -a "$LOG_FILE"
fi

# Step 2: Regenerate today's memory file
echo "[$(date)] Step 2: Regenerating memory for $TODAY..." | tee -a "$LOG_FILE"

export DISCORD_SOUL_DB="$SQLITE_DB"
export DISCORD_SOUL_MEMORY="$MEMORY_PATH"

python3 "$SCRIPT_DIR/generate_daily_memory.py" "$TODAY" 2>&1 | tee -a "$LOG_FILE"

# Check if file was created
if [ -f "$MEMORY_PATH/$TODAY.md" ]; then
    SIZE=$(du -h "$MEMORY_PATH/$TODAY.md" | cut -f1)
    echo "[$(date)] Created: $MEMORY_PATH/$TODAY.md ($SIZE)" | tee -a "$LOG_FILE"
else
    echo "[$(date)] Warning: No messages for today" | tee -a "$LOG_FILE"
fi

# Step 3: Wake the agent (if OpenClaw available)
if command -v openclaw &> /dev/null; then
    echo "[$(date)] Step 3: Waking agent..." | tee -a "$LOG_FILE"
    openclaw gateway wake --text "New Discord activity for $TODAY" --mode next-heartbeat 2>&1 || true
else
    echo "[$(date)] Step 3: Skipping wake (OpenClaw not found)" | tee -a "$LOG_FILE"
fi

echo "[$(date)] =====================================" | tee -a "$LOG_FILE"
echo "[$(date)] Pipeline complete!" | tee -a "$LOG_FILE"
echo "[$(date)] =====================================" | tee -a "$LOG_FILE"
