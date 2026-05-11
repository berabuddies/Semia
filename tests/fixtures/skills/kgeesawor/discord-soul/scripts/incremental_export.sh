#!/bin/bash
# incremental_export.sh
# Incremental Discord export: fetches only new messages since last run
# Merges into the master SQLite database using rich ingestion
#
# Usage: ./incremental_export.sh --guild GUILD_ID --db ./discord.sqlite
#
# Environment variables (alternative to flags):
#   DISCORD_GUILD_ID      Discord Guild/Server ID
#   DISCORD_SOUL_DB      Path to SQLite database
#   DISCORD_TOKEN_FILE    Path to token file (default: ~/.config/discord-exporter-token)
#   DISCORD_EXPORTER_CLI  Path to DiscordChatExporter.Cli

set -e

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --guild|-g)
            GUILD_ID="$2"
            shift 2
            ;;
        --db|-d)
            MASTER_DB="$2"
            shift 2
            ;;
        --hours|-h)
            HOURS_BACK="$2"
            shift 2
            ;;
        --token-file|-t)
            TOKEN_FILE="$2"
            shift 2
            ;;
        --exporter|-e)
            DCE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 --guild GUILD_ID --db ./discord.sqlite [--hours 6]"
            exit 1
            ;;
    esac
done

# Fallback to environment variables
GUILD_ID="${GUILD_ID:-$DISCORD_GUILD_ID}"
MASTER_DB="${MASTER_DB:-$DISCORD_SOUL_DB}"
TOKEN_FILE="${TOKEN_FILE:-${DISCORD_TOKEN_FILE:-$HOME/.config/discord-exporter-token}}"
DCE="${DCE:-${DISCORD_EXPORTER_CLI:-DiscordChatExporter.Cli}}"
HOURS_BACK="${HOURS_BACK:-6}"

# Validate
if [ -z "$GUILD_ID" ]; then
    echo "Error: No guild ID specified. Use --guild or set DISCORD_GUILD_ID"
    exit 1
fi

if [ -z "$MASTER_DB" ]; then
    echo "Error: No database specified. Use --db or set DISCORD_SOUL_DB"
    exit 1
fi

if [ ! -f "$TOKEN_FILE" ]; then
    echo "Error: Token file not found: $TOKEN_FILE"
    exit 1
fi

TOKEN=$(cat "$TOKEN_FILE")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$MASTER_DB")"
STATE_FILE="$BASE_DIR/.last-export-timestamp"
LOG_FILE="$BASE_DIR/incremental-export.log"

# Calculate after date
if [ -f "$STATE_FILE" ]; then
    LAST_EXPORT=$(cat "$STATE_FILE")
    AFTER_DATE="$LAST_EXPORT"
    echo "[$(date)] Using last export timestamp: $AFTER_DATE" | tee -a "$LOG_FILE"
else
    # First run or state lost: use hours_back
    AFTER_DATE=$(date -v-${HOURS_BACK}H +%Y-%m-%dT%H:%M:%S 2>/dev/null || date -d "-${HOURS_BACK} hours" +%Y-%m-%dT%H:%M:%S)
    echo "[$(date)] No state file, using ${HOURS_BACK}h lookback: $AFTER_DATE" | tee -a "$LOG_FILE"
fi

# Temp directory for this run
EXPORT_DIR="$BASE_DIR/incremental-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$EXPORT_DIR"

echo "[$(date)] Starting incremental export..." | tee -a "$LOG_FILE"
echo "[$(date)] Guild: $GUILD_ID" | tee -a "$LOG_FILE"
echo "[$(date)] Export dir: $EXPORT_DIR" | tee -a "$LOG_FILE"
echo "[$(date)] After: $AFTER_DATE" | tee -a "$LOG_FILE"

# Get all channels
CHANNELS=$($DCE channels -g $GUILD_ID -t "$TOKEN" 2>/dev/null | grep -E '^[0-9]+' | awk '{print $1}')
TOTAL=$(echo "$CHANNELS" | wc -l | tr -d ' ')

echo "[$(date)] Exporting $TOTAL channels..." | tee -a "$LOG_FILE"

# Export each channel (incremental)
EXPORTED=0
for CHANNEL_ID in $CHANNELS; do
    $DCE export \
        -c "$CHANNEL_ID" \
        -t "$TOKEN" \
        -f Json \
        --after "$AFTER_DATE" \
        --include-threads All \
        -o "${EXPORT_DIR}/" \
        2>&1 | grep -v "^$" || true
    EXPORTED=$((EXPORTED + 1))
    
    # Progress every 10 channels
    if [ $((EXPORTED % 10)) -eq 0 ]; then
        echo "[$(date)] Progress: $EXPORTED/$TOTAL channels" | tee -a "$LOG_FILE"
    fi
done

echo "[$(date)] Export complete. Checking for new messages..." | tee -a "$LOG_FILE"

# Count exported files
FILE_COUNT=$(ls "$EXPORT_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')

if [ "$FILE_COUNT" -gt 0 ]; then
    echo "[$(date)] Found $FILE_COUNT files with new messages" | tee -a "$LOG_FILE"
    
    # Get message count before merge
    BEFORE_COUNT=$(sqlite3 "$MASTER_DB" "SELECT COUNT(*) FROM messages;" 2>/dev/null || echo "0")
    
    # Merge into master SQLite using rich ingestion
    echo "[$(date)] Merging into master database..." | tee -a "$LOG_FILE"
    python3 "$SCRIPT_DIR/ingest_rich.py" --input "$EXPORT_DIR" --output "$MASTER_DB" --append 2>&1 | tail -5 | tee -a "$LOG_FILE"
    
    # Get message count after merge
    AFTER_COUNT=$(sqlite3 "$MASTER_DB" "SELECT COUNT(*) FROM messages;")
    NEW_MESSAGES=$((AFTER_COUNT - BEFORE_COUNT))
    
    echo "[$(date)] Merged: $BEFORE_COUNT → $AFTER_COUNT (+$NEW_MESSAGES new)" | tee -a "$LOG_FILE"
else
    echo "[$(date)] No new messages found" | tee -a "$LOG_FILE"
    NEW_MESSAGES=0
fi

# Update state file with current timestamp
date +%Y-%m-%dT%H:%M:%S > "$STATE_FILE"
echo "[$(date)] Updated state file: $(cat $STATE_FILE)" | tee -a "$LOG_FILE"

# Cleanup old incremental dirs (keep last 5)
cd "$BASE_DIR"
ls -dt incremental-* 2>/dev/null | tail -n +6 | xargs rm -rf 2>/dev/null || true

echo "[$(date)] Done!" | tee -a "$LOG_FILE"
echo ""
echo "=== Summary ==="
echo "Files exported: $FILE_COUNT"
echo "Messages before: ${BEFORE_COUNT:-N/A}"
echo "Messages after: ${AFTER_COUNT:-N/A}"
echo "New messages: ${NEW_MESSAGES:-0}"
