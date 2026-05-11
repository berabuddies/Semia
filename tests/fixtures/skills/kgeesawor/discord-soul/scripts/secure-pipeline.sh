#!/bin/bash
# discord-intel/scripts/secure-pipeline.sh
# Full security pipeline: JSON → SQLite → Regex → Haiku → LanceDB
# Usage: ./secure-pipeline.sh <export_dir> [output_dir]

set -e

EXPORT_DIR="${1:?Usage: $0 <export_dir> [output_dir]}"
OUTPUT_DIR="${2:-./discord-intel-output}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Output paths
SQLITE_DB="$OUTPUT_DIR/discord.db"
LANCE_DIR="$OUTPUT_DIR/vectors"
LOG_FILE="$OUTPUT_DIR/pipeline.log"

mkdir -p "$OUTPUT_DIR"

echo "=== Discord Intel Security Pipeline ===" | tee "$LOG_FILE"
echo "Export dir: $EXPORT_DIR" | tee -a "$LOG_FILE"
echo "Output dir: $OUTPUT_DIR" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Step 1: SQLite
echo "→ Step 1: SQLite conversion" | tee -a "$LOG_FILE"
python3 "$SCRIPT_DIR/to-sqlite.py" "$EXPORT_DIR" "$SQLITE_DB" 2>&1 | tee -a "$LOG_FILE"

TOTAL=$(sqlite3 "$SQLITE_DB" "SELECT COUNT(*) FROM messages;")
echo "  Loaded $TOTAL messages" | tee -a "$LOG_FILE"

# Step 2: Regex filter
echo "" | tee -a "$LOG_FILE"
echo "→ Step 2: Regex pre-filter" | tee -a "$LOG_FILE"
python3 "$SCRIPT_DIR/regex-filter.py" --update --db "$SQLITE_DB" 2>&1 | tee -a "$LOG_FILE"

REGEX_FLAGGED=$(sqlite3 "$SQLITE_DB" "SELECT COUNT(*) FROM messages WHERE safety_status = 'regex_flagged';")
echo "  Regex flagged: $REGEX_FLAGGED" | tee -a "$LOG_FILE"

# Step 3: Haiku evaluation
echo "" | tee -a "$LOG_FILE"
echo "→ Step 3: Haiku safety evaluation" | tee -a "$LOG_FILE"

if [ -n "$ANTHROPIC_API_KEY" ]; then
    python3 "$SCRIPT_DIR/evaluate-safety.py" "$SQLITE_DB" --threshold 0.6 2>&1 | tee -a "$LOG_FILE"
else
    echo "  ⚠️ ANTHROPIC_API_KEY not set, marking as unverified" | tee -a "$LOG_FILE"
    sqlite3 "$SQLITE_DB" "UPDATE messages SET safety_status = 'unverified' WHERE safety_status = 'pending';"
fi

# Step 4: LanceDB index
echo "" | tee -a "$LOG_FILE"
echo "→ Step 4: LanceDB indexing (safe only)" | tee -a "$LOG_FILE"
python3 "$SCRIPT_DIR/index-to-lancedb.py" "$SQLITE_DB" "$LANCE_DIR" 2>&1 | tee -a "$LOG_FILE"

# Summary
echo "" | tee -a "$LOG_FILE"
echo "=== Pipeline Complete ===" | tee -a "$LOG_FILE"
sqlite3 "$SQLITE_DB" "
SELECT 'Total: ' || COUNT(*) FROM messages
UNION ALL SELECT '  safe: ' || COUNT(*) FROM messages WHERE safety_status = 'safe'
UNION ALL SELECT '  regex_flagged: ' || COUNT(*) FROM messages WHERE safety_status = 'regex_flagged'
UNION ALL SELECT '  flagged: ' || COUNT(*) FROM messages WHERE safety_status = 'flagged'
UNION ALL SELECT '  pending: ' || COUNT(*) FROM messages WHERE safety_status = 'pending'
UNION ALL SELECT '  unverified: ' || COUNT(*) FROM messages WHERE safety_status = 'unverified';
" | tee -a "$LOG_FILE"

echo "" | tee -a "$LOG_FILE"
echo "Output:" | tee -a "$LOG_FILE"
echo "  SQLite: $SQLITE_DB" | tee -a "$LOG_FILE"
echo "  LanceDB: $LANCE_DIR" | tee -a "$LOG_FILE"
echo "  Log: $LOG_FILE" | tee -a "$LOG_FILE"
