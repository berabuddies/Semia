#!/bin/bash
# Ryot Automation Setup
# Auto-configure cron jobs for daily/weekly reports

set -e

SKILL_DIR="/home/node/clawd/skills/ryot"
CONFIG_FILE="/home/node/clawd/config/ryot.json"

echo "🔧 RYOT AUTOMATION SETUP"
echo ""

# Check config exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Error: Ryot config not found at $CONFIG_FILE"
    echo "Please create it first with:"
    echo '{"url": "https://your-ryot-instance.com", "api_token": "YOUR_TOKEN"}'
    exit 1
fi

echo "✅ Config found"
echo ""

# Parse dry-run flag
DRY_RUN=false
if [ "$1" = "--dry-run" ]; then
    DRY_RUN=true
    echo "🔍 DRY RUN MODE - No changes will be made"
    echo ""
fi

# Get WhatsApp number
echo "📱 WhatsApp number for notifications?"
echo "   (Press Enter to skip automation)"
read -r WHATSAPP_NUMBER

if [ -z "$WHATSAPP_NUMBER" ]; then
    echo "⏭️  Skipping automation setup"
    exit 0
fi

echo ""
echo "📋 CRON JOBS TO CREATE:"
echo ""
echo "1️⃣  Upcoming Episodes - Daily 07:30"
echo "    📺 Shows new episodes airing today"
echo ""
echo "2️⃣  Weekly Stats - Monday 08:00"
echo "    📊 Your weekly viewing statistics"
echo ""
echo "3️⃣  Recent Activity - Daily 20:00"
echo "    🕒 What you watched/read recently"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo "🔍 Dry run complete. No jobs created."
    exit 0
fi

echo "Proceed with setup? (y/n)"
read -r CONFIRM

if [ "$CONFIRM" != "y" ]; then
    echo "❌ Setup cancelled"
    exit 0
fi

echo ""
echo "🚀 Creating cron jobs..."

# Helper function to create cron jobs
create_cron_job() {
    local name="$1"
    local cron_expr="$2"
    local script="$3"
    local description="$4"
    
    openclaw cron add \
        --name "$name" \
        --cron "$cron_expr" \
        --message "Esegui lo script $SKILL_DIR/scripts/$script e inviami l'output formattato per WhatsApp." \
        --model "gemini-flash" \
        --announce \
        --channel "whatsapp" \
        --to "$WHATSAPP_NUMBER" 2>&1 | grep -q "OK" && echo "✅ $description" || echo "⚠️  Failed: $description"
}

# Create jobs
create_cron_job \
    "Ryot - Upcoming Episodes" \
    "30 7 * * *" \
    "ryot_calendar.py upcoming" \
    "Upcoming episodes (07:30 daily)"

create_cron_job \
    "Ryot - Weekly Stats" \
    "0 8 * * 1" \
    "ryot_stats.py analytics" \
    "Weekly stats (Monday 08:00)"

create_cron_job \
    "Ryot - Recent Activity" \
    "0 20 * * *" \
    "ryot_stats.py recent" \
    "Recent activity (20:00 daily)"

echo ""
echo "✅ SETUP COMPLETE!"
echo ""
echo "📋 Active automation:"
echo "   • Daily upcoming episodes (07:30)"
echo "   • Weekly statistics (Monday 08:00)"
echo "   • Daily recent activity (20:00)"
echo ""
echo "🔧 Manage jobs:"
echo "   openclaw cron list"
echo "   openclaw cron remove <job-id>"
echo ""
echo "🎉 Ryot automation is ready!"
