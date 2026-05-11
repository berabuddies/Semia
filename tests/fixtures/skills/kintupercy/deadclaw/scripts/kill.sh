#!/usr/bin/env bash
# ============================================================================
# DeadClaw — kill.sh
# Core emergency kill script for OpenClaw agents.
#
# What this script does:
#   1. Finds and kills all running OpenClaw agent processes (native + Docker)
#   2. Backs up the current crontab, then clears all OpenClaw cron jobs
#   3. Kills all active OpenClaw agent sessions
#   4. Writes a timestamped incident log to deadclaw.log
#   5. Sends a confirmation message back to the triggering channel
#
# Supports both:
#   - Native OpenClaw installs (processes on the host)
#   - Docker-based OpenClaw installs (Hostinger VPS, etc.)
#
# Usage:
#   ./kill.sh                          # Execute the kill
#   ./kill.sh --dry-run                # Log what would happen, don't kill anything
#   ./kill.sh --trigger-source slack   # Specify the trigger source for logging
#   ./kill.sh --trigger-method message # Specify the trigger method for logging
#
# This script is idempotent — running it twice is safe and won't cause errors.
# ============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Directory where this script lives (used to find deadclaw.log and other scripts)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="${SKILL_DIR}/deadclaw.log"
BACKUP_DIR="${SKILL_DIR}/backups"

# Defaults for logging context
DRY_RUN=false
TRIGGER_SOURCE="${DEADCLAW_TRIGGER_SOURCE:-unknown}"
TRIGGER_METHOD="${DEADCLAW_TRIGGER_METHOD:-manual}"

# ---------------------------------------------------------------------------
# Parse command-line arguments
# ---------------------------------------------------------------------------

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --trigger-source)
            TRIGGER_SOURCE="$2"
            shift 2
            ;;
        --trigger-method)
            TRIGGER_METHOD="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

# Timestamp in ISO 8601 format
timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

# Log a message to both stderr (for display) and the incident log file.
# Using stderr so log messages don't interfere with function return values
# captured via $(...) subshells.
log_event() {
    local msg="$1"
    echo "[$(timestamp)] $msg" >&2
    echo "[$(timestamp)] $msg" >> "$LOG_FILE"
}

# Detect the operating system so we can use the right process management commands
detect_os() {
    case "$(uname -s)" in
        Darwin*) echo "macos" ;;
        Linux*)  echo "linux" ;;
        *)       echo "unknown" ;;
    esac
}

# ---------------------------------------------------------------------------
# Docker support — detect and manage OpenClaw Docker containers
# ---------------------------------------------------------------------------

# Find running Docker containers that match OpenClaw patterns
find_openclaw_containers() {
    if ! command -v docker &>/dev/null; then
        return
    fi
    docker ps --filter "name=openclaw" --format "{{.Names}}" 2>/dev/null || true
}

# Kill sessions and stop Docker containers
kill_docker() {
    local containers
    containers=$(find_openclaw_containers)
    local count=0

    if [[ -z "$containers" ]]; then
        log_event "DOCKER: No OpenClaw Docker containers found."
        echo "0"
        return
    fi

    while IFS= read -r container; do
        [[ -n "$container" ]] || continue

        if [[ "$DRY_RUN" == true ]]; then
            local status
            status=$(docker inspect --format '{{.State.Status}}' "$container" 2>/dev/null || echo "unknown")
            log_event "DRY-RUN: Would stop Docker container: $container (status: $status)"
        else
            # Graceful: kill sessions inside the container first
            docker exec "$container" openclaw session kill-all &>/dev/null || true
            log_event "DOCKER: Killed sessions in container: $container"

            # Stop the container (10s grace period for clean shutdown)
            docker stop -t 10 "$container" &>/dev/null || true
            log_event "DOCKER: Stopped container: $container"
        fi
        count=$((count + 1))
    done <<< "$containers"

    log_event "DOCKER: ${count} OpenClaw containers stopped."
    echo "$count"
}

# Send a confirmation message back to the triggering channel.
# Uses OpenClaw's messaging hooks if available, falls back to stdout.
# Tries Docker exec if openclaw isn't available on the host.
send_confirmation() {
    local message="$1"

    # Try OpenClaw's messaging API on the host first
    if command -v openclaw &>/dev/null; then
        openclaw message send \
            --channel "${TRIGGER_SOURCE}" \
            --text "${message}" 2>/dev/null || true
    else
        # Try via a running Docker container
        local container
        container=$(find_openclaw_containers | head -1)
        if [[ -n "$container" ]]; then
            docker exec "$container" openclaw message send \
                --channel "${TRIGGER_SOURCE}" \
                --text "${message}" 2>/dev/null || true
        fi
    fi

    # Always print to stdout as a fallback
    echo "$message"
}

# ---------------------------------------------------------------------------
# Step 1: Find all running OpenClaw agent processes
# ---------------------------------------------------------------------------

find_openclaw_processes() {
    # Look for processes matching common OpenClaw agent patterns.
    # We search for multiple patterns to catch agents started different ways.
    local pids=()

    # Pattern 1: Processes with "openclaw" in the command line
    while IFS= read -r pid; do
        [[ -n "$pid" ]] && pids+=("$pid")
    done < <(pgrep -f "openclaw[-_ ]agent" 2>/dev/null || true)

    # Pattern 2: Processes with "claw-agent" in the command line
    while IFS= read -r pid; do
        [[ -n "$pid" ]] && pids+=("$pid")
    done < <(pgrep -f "claw-agent" 2>/dev/null || true)

    # Pattern 3: Processes with "openclaw-skill" in the command line
    while IFS= read -r pid; do
        [[ -n "$pid" ]] && pids+=("$pid")
    done < <(pgrep -f "openclaw-skill" 2>/dev/null || true)

    # Pattern 4: Processes with "clawdbot" in the command line
    while IFS= read -r pid; do
        [[ -n "$pid" ]] && pids+=("$pid")
    done < <(pgrep -f "clawdbot" 2>/dev/null || true)

    # Pattern 5: Processes with "moltbot" in the command line
    while IFS= read -r pid; do
        [[ -n "$pid" ]] && pids+=("$pid")
    done < <(pgrep -f "moltbot" 2>/dev/null || true)

    # Pattern 6: Processes with OpenClaw gateway in the command line
    while IFS= read -r pid; do
        [[ -n "$pid" ]] && pids+=("$pid")
    done < <(pgrep -f "openclaw.*gateway" 2>/dev/null || true)

    # Pattern 7: Processes matching the OPENCLAW_PROCESS_PATTERN env var
    # (allows users to add custom patterns for their specific setup)
    if [[ -n "${OPENCLAW_PROCESS_PATTERN:-}" ]]; then
        while IFS= read -r pid; do
            [[ -n "$pid" ]] && pids+=("$pid")
        done < <(pgrep -f "${OPENCLAW_PROCESS_PATTERN}" 2>/dev/null || true)
    fi

    # Deduplicate PIDs (guard against empty array)
    if [[ ${#pids[@]} -eq 0 ]]; then
        return
    fi
    printf '%s\n' "${pids[@]}" | sort -u
}

# ---------------------------------------------------------------------------
# Step 2: Kill all OpenClaw processes
# ---------------------------------------------------------------------------

kill_processes() {
    local pids
    pids=$(find_openclaw_processes)
    local count=0
    local killed_pids=()

    if [[ -z "$pids" ]]; then
        log_event "KILL: No OpenClaw agent processes found."
        echo "0"
        return
    fi

    while IFS= read -r pid; do
        if [[ "$DRY_RUN" == true ]]; then
            log_event "DRY-RUN: Would kill PID $pid ($(ps -p "$pid" -o comm= 2>/dev/null || echo 'unknown'))"
        else
            # Send SIGTERM first (graceful), then SIGKILL after 5 seconds if still alive
            if kill -TERM "$pid" 2>/dev/null; then
                killed_pids+=("$pid")
                count=$((count + 1))
            fi
        fi
    done <<< "$pids"

    # If not a dry run, wait briefly then force-kill any survivors
    if [[ "$DRY_RUN" == false && ${#killed_pids[@]} -gt 0 ]]; then
        sleep 2
        for pid in "${killed_pids[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid" 2>/dev/null || true
                log_event "KILL: Force-killed stubborn process PID $pid"
            fi
        done
    fi

    log_event "KILL: ${count} OpenClaw processes terminated. PIDs: ${killed_pids[*]:-none}"
    echo "$count"
}

# ---------------------------------------------------------------------------
# Step 3: Back up and clear OpenClaw cron jobs
# ---------------------------------------------------------------------------

pause_cron_jobs() {
    local os
    os=$(detect_os)
    local cron_count=0

    # Create backup directory if it doesn't exist
    mkdir -p "$BACKUP_DIR"

    # Back up the current crontab before touching anything
    local backup_file="${BACKUP_DIR}/deadclaw-crontab-backup-$(date +%Y%m%d-%H%M%S).txt"

    if crontab -l &>/dev/null; then
        crontab -l > "$backup_file" 2>/dev/null || true
        log_event "CRON: Crontab backed up to ${backup_file}"

        # Count OpenClaw-related cron entries
        # Note: grep -c outputs "0" with exit code 1 when no matches found.
        # Using `|| true` avoids capturing a second "0" from a fallback echo.
        cron_count=$(grep -c -i "openclaw\|claw-agent\|clawdbot\|moltbot" "$backup_file" 2>/dev/null || true)
        cron_count=${cron_count:-0}

        if [[ "$DRY_RUN" == true ]]; then
            log_event "DRY-RUN: Would remove ${cron_count} OpenClaw cron entries"
        else
            # Surgical removal: only OpenClaw-related entries, preserve everything else
            crontab -l 2>/dev/null | grep -v -i "openclaw\|claw-agent\|clawdbot\|moltbot" | crontab - 2>/dev/null || true
            log_event "CRON: ${cron_count} OpenClaw cron entries removed"
        fi
    else
        log_event "CRON: No crontab found. Nothing to back up or clear."
    fi

    # Handle OS-specific scheduled tasks
    if [[ "$os" == "macos" ]]; then
        # Pause any OpenClaw launchd agents
        local agents_paused=0
        for plist in ~/Library/LaunchAgents/com.openclaw.*; do
            [[ -f "$plist" ]] || continue
            if [[ "$DRY_RUN" == true ]]; then
                log_event "DRY-RUN: Would unload launchd agent: $(basename "$plist")"
            else
                launchctl unload "$plist" 2>/dev/null || true
                log_event "CRON: Unloaded launchd agent: $(basename "$plist")"
            fi
            agents_paused=$((agents_paused + 1))
        done
        cron_count=$((cron_count + agents_paused))
    elif [[ "$os" == "linux" ]]; then
        # Pause any OpenClaw systemd user services
        local services_paused=0
        while IFS= read -r service; do
            [[ -n "$service" ]] || continue
            if [[ "$DRY_RUN" == true ]]; then
                log_event "DRY-RUN: Would stop systemd service: $service"
            else
                systemctl --user stop "$service" 2>/dev/null || true
                systemctl --user disable "$service" 2>/dev/null || true
                log_event "CRON: Stopped systemd service: $service"
            fi
            services_paused=$((services_paused + 1))
        done < <(systemctl --user list-units --type=service --no-legend 2>/dev/null | grep -i "openclaw\|claw-agent\|clawdbot\|moltbot" | awk '{print $1}' || true)
        cron_count=$((cron_count + services_paused))
    fi

    echo "$cron_count"
}

# ---------------------------------------------------------------------------
# Step 4: Kill active OpenClaw sessions
# ---------------------------------------------------------------------------

kill_sessions() {
    # If OpenClaw CLI is available on host, use it to terminate active sessions
    if command -v openclaw &>/dev/null; then
        if [[ "$DRY_RUN" == true ]]; then
            local session_list
            session_list=$(openclaw session list --format json 2>/dev/null || echo "[]")
            log_event "DRY-RUN: Would terminate all active OpenClaw sessions: ${session_list}"
        else
            openclaw session kill-all 2>/dev/null || true
            log_event "SESSIONS: All active OpenClaw sessions terminated"
        fi
    else
        # Docker sessions are already killed in kill_docker() before container stop.
        # If there were no Docker containers either, note it.
        local containers
        containers=$(find_openclaw_containers)
        if [[ -z "$containers" ]]; then
            log_event "SESSIONS: OpenClaw CLI not found and no Docker containers — skipping session cleanup"
        else
            log_event "SESSIONS: Sessions killed via Docker (handled in container stop sequence)"
        fi
    fi
}

# ---------------------------------------------------------------------------
# Step 5: Get current token spend (for the incident log)
# ---------------------------------------------------------------------------

get_token_spend() {
    # Try to read token spend from OpenClaw's metrics if available
    if command -v openclaw &>/dev/null; then
        openclaw metrics token-spend --format plain 2>/dev/null || echo "unknown"
    else
        # Try via Docker container
        local container
        container=$(find_openclaw_containers | head -1)
        if [[ -n "$container" ]]; then
            docker exec "$container" openclaw metrics token-spend --format plain 2>/dev/null || echo "unknown"
        elif [[ -f "${OPENCLAW_WORKSPACE:-/tmp}/.openclaw/metrics/tokens.log" ]]; then
            tail -1 "${OPENCLAW_WORKSPACE:-/tmp}/.openclaw/metrics/tokens.log" 2>/dev/null || echo "unknown"
        else
            echo "unknown"
        fi
    fi
}

# ---------------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------------

main() {
    local ts
    ts=$(timestamp)

    echo ""
    echo "============================================"
    if [[ "$DRY_RUN" == true ]]; then
        echo "  DeadClaw — DRY RUN (no actions taken)"
    else
        echo "  DeadClaw — Emergency Kill Activated"
    fi
    echo "  ${ts}"
    echo "============================================"
    echo ""

    # Write incident log header
    log_event "=========================================="
    log_event "DEADCLAW KILL EVENT"
    log_event "Trigger source: ${TRIGGER_SOURCE}"
    log_event "Trigger method: ${TRIGGER_METHOD}"
    log_event "Dry run: ${DRY_RUN}"
    log_event "=========================================="

    # Execute the kill sequence — both native processes and Docker containers
    local processes_killed
    processes_killed=$(kill_processes)

    local containers_killed
    containers_killed=$(kill_docker)

    local cron_paused
    cron_paused=$(pause_cron_jobs)

    kill_sessions

    local token_spend
    token_spend=$(get_token_spend)

    # Combine native + Docker counts for the summary
    local total_killed=$((processes_killed + containers_killed))

    # Write summary to incident log
    log_event "SUMMARY: ${processes_killed} processes killed, ${containers_killed} containers stopped, ${cron_paused} cron jobs paused, token spend: ${token_spend}"
    log_event "=========================================="

    # Build and send the confirmation message
    local prefix=""
    [[ "$DRY_RUN" == true ]] && prefix="[DRY-RUN] "

    local confirmation
    confirmation="${prefix}🔴 DeadClaw activated. All agents stopped. ${ts} — ${total_killed} killed (${processes_killed} processes, ${containers_killed} containers). ${cron_paused} cron jobs paused. See deadclaw.log for full report."

    send_confirmation "$confirmation"

    # Stop the watchdog too (if it's running), since all agents are dead
    if [[ "$DRY_RUN" == false ]]; then
        "${SCRIPT_DIR}/watchdog.sh" stop 2>/dev/null || true
    fi
}

main "$@"
exit 0
