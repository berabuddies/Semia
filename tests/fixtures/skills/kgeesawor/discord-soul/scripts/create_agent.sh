#!/bin/bash
# create_agent.sh
# Full pipeline to create a Discord Community Agent from scratch
#
# Usage: ./create_agent.sh --name "my-community" --guild GUILD_ID --output ./agents/
#
# This will:
# 1. Create agent workspace structure
# 2. Export Discord server history
# 3. Ingest to SQLite with rich data
# 4. Generate daily memory files
# 5. Generate simulation prompts
#
# After running, you need to:
# 1. Run simulation prompts to grow SOUL.md etc.
# 2. Add agent config to openclaw.json
# 3. Create chat binding (Telegram topic, etc.)

set -e

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --name|-n)
            AGENT_NAME="$2"
            shift 2
            ;;
        --guild|-g)
            GUILD_ID="$2"
            shift 2
            ;;
        --output|-o)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --token-file|-t)
            TOKEN_FILE="$2"
            shift 2
            ;;
        --skip-export)
            SKIP_EXPORT=1
            shift
            ;;
        --export-dir|-e)
            EXPORT_DIR="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate required args
if [ -z "$AGENT_NAME" ]; then
    echo "Error: Agent name required. Use --name"
    exit 1
fi

if [ -z "$GUILD_ID" ] && [ -z "$SKIP_EXPORT" ] && [ -z "$EXPORT_DIR" ]; then
    echo "Error: Guild ID required for export. Use --guild or --skip-export with --export-dir"
    exit 1
fi

OUTPUT_DIR="${OUTPUT_DIR:-./agents}"
TOKEN_FILE="${TOKEN_FILE:-$HOME/.config/discord-exporter-token}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

AGENT_PATH="$OUTPUT_DIR/$AGENT_NAME"
DATA_PATH="$OUTPUT_DIR/$AGENT_NAME-data"
SQLITE_DB="$DATA_PATH/discord.sqlite"

echo "=============================================="
echo "Creating Discord Community Agent: $AGENT_NAME"
echo "=============================================="
echo ""

# Step 1: Create directory structure
echo "Step 1: Creating agent workspace..."
mkdir -p "$AGENT_PATH/memory"
mkdir -p "$AGENT_PATH/scripts"
mkdir -p "$DATA_PATH/export"

# Create template files
cat > "$AGENT_PATH/SOUL.md" << 'EOF'
# SOUL.md — Who I Am

*This file evolves as the community defines itself.*

## I Am [Community Name]

*[Identity emerges from conversations]*

## My Voice

*[Tone emerges from how members talk]*

## My Values

*[Crystallizes from repeated patterns]*
EOF

cat > "$AGENT_PATH/MEMORY.md" << 'EOF'
# MEMORY.md — Long-Term Memory

## Origin
- **Born:** YYYY-MM-DD
- **Founder:** @username
- **Purpose:** [Community purpose]

## Milestones
*[Populated as significant moments occur]*
EOF

cat > "$AGENT_PATH/LEARNINGS.md" << 'EOF'
# LEARNINGS.md — What I've Learned

## Patterns
*[Observations about community behavior]*

## Cultural Norms
*[Unwritten rules and traditions]*
EOF

cat > "$AGENT_PATH/AGENTS.md" << 'EOF'
# AGENTS.md — Key Figures

## Founders & Leaders
*[Notable people and their roles]*

## Emerging Voices
*[New contributors to watch]*
EOF

cat > "$AGENT_PATH/TOOLS.md" << 'EOF'
# TOOLS.md — How We Operate

## Channels
*[What each channel is for]*

## Rituals
*[Regular events and traditions]*

## Integrations
*[Bots, webhooks, etc.]*
EOF

cat > "$AGENT_PATH/HEARTBEAT.md" << 'EOF'
# HEARTBEAT.md — Periodic Maintenance

## On Heartbeat
1. Check for new memory files
2. Update LEARNINGS.md with new patterns
3. Prune old memories to MEMORY.md
4. Reply HEARTBEAT_OK if nothing to report
EOF

echo "  Created: $AGENT_PATH/"
echo ""

# Step 2: Export Discord (unless skipped)
if [ -z "$SKIP_EXPORT" ]; then
    echo "Step 2: Exporting Discord server..."
    
    if [ ! -f "$TOKEN_FILE" ]; then
        echo "  Error: Token file not found: $TOKEN_FILE"
        echo "  Create it with your Discord token, then re-run"
        exit 1
    fi
    
    TOKEN=$(cat "$TOKEN_FILE")
    DCE="${DISCORD_EXPORTER_CLI:-DiscordChatExporter.Cli}"
    
    $DCE exportguild \
        --guild "$GUILD_ID" \
        --token "$TOKEN" \
        --format Json \
        --output "$DATA_PATH/export/" \
        --include-threads All \
        --media false
    
    EXPORT_DIR="$DATA_PATH/export"
    echo "  Exported to: $EXPORT_DIR"
else
    if [ -z "$EXPORT_DIR" ]; then
        echo "Error: When using --skip-export, provide --export-dir"
        exit 1
    fi
    echo "Step 2: Skipping export, using: $EXPORT_DIR"
fi
echo ""

# Step 3: Ingest to SQLite
echo "Step 3: Ingesting to SQLite..."
python3 "$SCRIPT_DIR/ingest_rich.py" --input "$EXPORT_DIR" --output "$SQLITE_DB"
echo "  Database: $SQLITE_DB"
echo ""

# Step 4: Generate memory files
echo "Step 4: Generating daily memory files..."
python3 "$SCRIPT_DIR/generate_daily_memory.py" --all \
    --db "$SQLITE_DB" \
    --out "$AGENT_PATH/memory/"

MEMORY_COUNT=$(ls "$AGENT_PATH/memory/"*.md 2>/dev/null | wc -l | tr -d ' ')
echo "  Generated: $MEMORY_COUNT daily files"
echo ""

# Step 5: Generate simulation prompts
echo "Step 5: Generating simulation prompts..."
python3 "$SCRIPT_DIR/simulate_growth.py" --agent "$AGENT_PATH"
echo ""

# Summary
echo "=============================================="
echo "Agent created successfully!"
echo "=============================================="
echo ""
echo "Agent workspace: $AGENT_PATH"
echo "Data directory:  $DATA_PATH"
echo "SQLite database: $SQLITE_DB"
echo "Memory files:    $MEMORY_COUNT days"
echo ""
echo "Next steps:"
echo "  1. Run simulation prompts in $AGENT_PATH/simulation/"
echo "     (Process each day in order to grow SOUL.md, etc.)"
echo ""
echo "  2. Add agent to openclaw.json:"
echo "     {"
echo "       \"id\": \"$AGENT_NAME\","
echo "       \"workspace\": \"$AGENT_PATH\","
echo "       \"memorySearch\": {\"enabled\": true, \"sources\": [\"memory\"]}"
echo "     }"
echo ""
echo "  3. Create chat binding (Telegram topic, etc.)"
echo ""
echo "  4. Set up incremental cron:"
echo "     ./update_agent_memory.sh --agent $AGENT_PATH --db $SQLITE_DB --guild $GUILD_ID"
