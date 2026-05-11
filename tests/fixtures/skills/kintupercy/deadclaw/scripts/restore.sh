#!/usr/bin/env bash
# ============================================================================
# DeadClaw — restore.sh
# Post-kill recovery script. Restores the backed-up crontab and optionally
# restarts previously running agents.
#
# What this script does:
#   1. Shows what will be restored (crontab entries, agent list)
#   2. Waits for explicit confirmation before proceeding
#   3. Restores the most recent crontab backup
#   4. Restarts the watchdog (optional)
#   5. Sends a confirmation message
#
# Usage:
#   ./restore.sh                # Interactive restore with confirmation prompt
#   ./restore.sh --dry-run      # Show what would be restored, don't do anything
#   ./restore.sh --confirm      # Skip the confirmation prompt (for automation)
#
# Safety: This script never restarts anything without confirmation. After a
# kill event, you want to be sure before bringing things back online.
# ============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="${SKILL_DIR}/deadclaw.log"
BACKUP_DIR="${SKILL_DIR}/backups"

DRY_RUN=false
AUTO_CONFIRM=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)  DRY_RUN=true; shift ;;
        --confirm)  AUTO_CONFIRM=true; shift ;;
        *)          shift ;;
    esac
done

timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

log_event() {
    local msg="$1"
    echo "[$(timestamp)] RESTORE: $msg" >> "$LOG_FILE"
}

send_message() {
    local message="$1"
    if command -v openclaw &>/dev/null; then
        openclaw message broadcast --text "${message}" 2>/dev/null || true
    else
        # Try via Docker container
        local container
        container=$(find_openclaw_containers | head -1)
        if [[ -n "$container" ]]; then
            docker exec "$container" openclaw message broadcast --text "${message}" 2>/dev/null || true
        fi
    fi
    echo "$message"
}

# Find running OpenClaw Docker containers
find_openclaw_containers() {
    if ! command -v docker &>/dev/null; then
        return
    fi
    docker ps --filter "name=openclaw" --format "{{.Names}}" 2>/dev/null || true
}

# Find stopped OpenClaw Docker containers
find_stopped_containers() {
    if ! command -v docker &>/dev/null; then
        return
    fi
    docker ps -a --filter "name=openclaw" --filter "status=exited" --format "{{.Names}}" 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# Step 1: Find the most recent crontab backup
# ---------------------------------------------------------------------------

find_latest_backup() {
    if [[ ! -d "$BACKUP_DIR" ]]; then
        echo ""
        return
    fi

    # Find the newest backup file
    ls -t "${BACKUP_DIR}"/deadclaw-crontab-backup-*.txt 2>/dev/null | head -1
}

# ---------------------------------------------------------------------------
# Step 2: Show what will be restored
# ---------------------------------------------------------------------------

show_restore_plan() {
    local backup_file="$1"

    echo ""
    echo "============================================"
    echo "  DeadClaw — Restore Plan"
    echo "============================================"
    echo ""

    if [[ -n "$backup_file" && -f "$backup_file" ]]; then
        local entry_count
        entry_count=$(wc -l < "$backup_file" | tr -d ' ')
        echo "Crontab backup found: $(basename "$backup_file")"
        echo "  Contains ${entry_count} entries:"
        echo ""
        # Show the crontab entries (indent them for readability)
        while IFS= read -r line; do
            echo "    ${line}"
        done < "$backup_file"
        echo ""
    else
        echo "No crontab backup found. Nothing to restore."
        echo ""
    fi

    # Check for any OpenClaw launchd/systemd services that were disabled
    local os
    os=$(uname -s)
    if [[ "$os" == "Darwin" ]]; then
        local disabled_agents
        disabled_agents=$(find ~/Library/LaunchAgents -name "com.openclaw.*" 2>/dev/null || true)
        if [[ -n "$disabled_agents" ]]; then
            echo "LaunchAgents to re-enable:"
            echo "$disabled_agents" | while read -r f; do echo "    $(basename "$f")"; done
            echo ""
        fi
    elif [[ "$os" == "Linux" ]]; then
        local disabled_services
        disabled_services=$(systemctl --user list-unit-files --type=service 2>/dev/null | grep -i "openclaw\|claw-agent\|clawdbot\|moltbot" | grep "disabled" || true)
        if [[ -n "$disabled_services" ]]; then
            echo "Systemd services to re-enable:"
            echo "$disabled_services" | while read -r line; do echo "    $line"; done
            echo ""
        fi
    fi

    # Check for stopped Docker containers
    local stopped_containers
    stopped_containers=$(find_stopped_containers)
    if [[ -n "$stopped_containers" ]]; then
        echo "Docker containers to restart:"
        while IFS= read -r c; do
            [[ -n "$c" ]] && echo "    $c"
        done <<< "$stopped_containers"
        echo ""
    fi

    echo "Note: The watchdog will NOT auto-start. Start it manually after verifying stability."
    echo ""
}

# ---------------------------------------------------------------------------
# Step 3: Wait for confirmation
# ---------------------------------------------------------------------------

get_confirmation() {
    local backup_file="$1"

    if [[ "$AUTO_CONFIRM" == true ]]; then
        return 0
    fi

    if [[ "$DRY_RUN" == true ]]; then
        echo "[DRY-RUN] Would wait for confirmation here. Skipping."
        return 1  # Don't proceed in dry-run
    fi

    # Build a specific prompt showing what will be restored
    local prompt_detail="Restore"
    if [[ -n "$backup_file" && -f "$backup_file" ]]; then
        local job_count
        job_count=$(wc -l < "$backup_file" | tr -d ' ')
        # Extract timestamp from filename: deadclaw-crontab-backup-YYYYMMDD-HHMMSS.txt
        local backup_ts
        backup_ts=$(basename "$backup_file" | sed 's/deadclaw-crontab-backup-//;s/\.txt//')
        prompt_detail="Restore ${job_count} cron jobs from backup taken at ${backup_ts}"
    fi

    echo "============================================"
    echo "  ${prompt_detail}? (yes/no)"
    echo "============================================"
    echo ""

    read -r response
    case "$response" in
        confirm|yes|YES|y|Y)
            return 0
            ;;
        *)
            echo "Restore cancelled."
            log_event "Restore cancelled by user."
            return 1
            ;;
    esac
}

# ---------------------------------------------------------------------------
# Step 4: Execute the restore
# ---------------------------------------------------------------------------

do_restore() {
    local backup_file="$1"
    local restored_items=0

    log_event "Restore initiated."

    # Restore crontab
    if [[ -n "$backup_file" && -f "$backup_file" ]]; then
        crontab "$backup_file" 2>/dev/null
        if [[ $? -eq 0 ]]; then
            log_event "Crontab restored from ${backup_file}"
            echo "Crontab restored."
            restored_items=$((restored_items + 1))
        else
            log_event "Failed to restore crontab from ${backup_file}"
            echo "Warning: Failed to restore crontab."
        fi
    fi

    # Re-enable OS-specific services
    local os
    os=$(uname -s)
    if [[ "$os" == "Darwin" ]]; then
        for plist in ~/Library/LaunchAgents/com.openclaw.*; do
            [[ -f "$plist" ]] || continue
            launchctl load "$plist" 2>/dev/null || true
            log_event "Re-enabled launchd agent: $(basename "$plist")"
            restored_items=$((restored_items + 1))
        done
    elif [[ "$os" == "Linux" ]]; then
        while IFS= read -r service; do
            [[ -n "$service" ]] || continue
            local svc_name
            svc_name=$(echo "$service" | awk '{print $1}')
            systemctl --user enable "$svc_name" 2>/dev/null || true
            systemctl --user start "$svc_name" 2>/dev/null || true
            log_event "Re-enabled systemd service: ${svc_name}"
            restored_items=$((restored_items + 1))
        done < <(systemctl --user list-unit-files --type=service 2>/dev/null | grep -i "openclaw\|claw-agent\|clawdbot\|moltbot" | grep "disabled" || true)
    fi

    # Restart stopped Docker containers
    local stopped_containers
    stopped_containers=$(find_stopped_containers)
    if [[ -n "$stopped_containers" ]]; then
        while IFS= read -r container; do
            [[ -n "$container" ]] || continue
            docker start "$container" &>/dev/null || true
            log_event "Restarted Docker container: ${container}"
            echo "Docker container restarted: ${container}"
            restored_items=$((restored_items + 1))
        done <<< "$stopped_containers"

        # Wait for containers to be ready
        echo "Waiting for containers to initialize..."
        sleep 5
    fi

    # Attempt to restart the OpenClaw gateway process
    if command -v openclaw &>/dev/null; then
        if openclaw gateway start 2>/dev/null; then
            log_event "OpenClaw gateway restarted."
            echo "OpenClaw gateway restarted."
            restored_items=$((restored_items + 1))
        else
            log_event "Failed to restart OpenClaw gateway (may need manual start)."
            echo "Warning: Could not restart OpenClaw gateway. Start it manually."
        fi
    else
        # Try via Docker container (check running containers now)
        local running_container
        running_container=$(find_openclaw_containers | head -1)
        if [[ -n "$running_container" ]]; then
            log_event "OpenClaw gateway running inside Docker container: ${running_container}"
            echo "OpenClaw gateway running inside Docker container: ${running_container}"
        else
            log_event "OpenClaw CLI not found and no Docker containers — skipping gateway restart."
            echo "Note: OpenClaw CLI not found. Start the gateway manually."
        fi
    fi

    log_event "Restore complete. ${restored_items} items restored."

    # Send confirmation — don't auto-start the watchdog. After a kill event,
    # the user should verify things are stable before enabling auto-kill.
    local msg="DeadClaw restore complete. ${restored_items} items restored. All systems nominal. Start watchdog manually: ./scripts/watchdog.sh start"
    send_message "$msg"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
    local backup_file
    backup_file=$(find_latest_backup)

    show_restore_plan "$backup_file"

    if [[ "$DRY_RUN" == true ]]; then
        echo "[DRY-RUN] No changes made."
        exit 0
    fi

    if get_confirmation "$backup_file"; then
        do_restore "$backup_file"
    fi
}

main "$@"
