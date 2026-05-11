#!/usr/bin/env bash
# ============================================================================
# DeadClaw — watchdog.sh
# Background monitor daemon that auto-triggers the kill script when it detects
# dangerous conditions in running OpenClaw agents.
#
# What this script monitors (every 60 seconds):
#   1. Runaway loops — any agent running longer than 30 minutes
#   2. Token burn — token spend exceeding 50,000 in under 10 minutes
#   3. Unauthorized network calls — outbound connections to non-whitelisted domains
#   4. Sandbox escape — file writes outside the designated workspace
#
# Usage:
#   ./watchdog.sh start              # Start the watchdog daemon
#   ./watchdog.sh stop               # Stop the watchdog daemon
#   ./watchdog.sh status             # Check if watchdog is running
#   ./watchdog.sh start --dry-run    # Monitor and log but don't auto-kill
#
# The watchdog writes a PID file so it can be stopped and restarted cleanly.
# ============================================================================

set -uo pipefail

# ---------------------------------------------------------------------------
# Configuration — all overridable via environment variables
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="${SKILL_DIR}/deadclaw.log"
PID_FILE="${SKILL_DIR}/deadclaw-watchdog.pid"

# Thresholds (with sensible defaults)
MAX_RUNTIME_MIN="${DEADCLAW_MAX_RUNTIME_MIN:-30}"
MAX_TOKENS="${DEADCLAW_MAX_TOKENS:-50000}"
TOKEN_WINDOW_MIN="${DEADCLAW_TOKEN_WINDOW_MIN:-10}"
WHITELIST_FILE="${DEADCLAW_WHITELIST:-${SKILL_DIR}/network-whitelist.txt}"
WORKSPACE="${DEADCLAW_WORKSPACE:-${OPENCLAW_WORKSPACE:-}}"
CHECK_INTERVAL=60   # seconds between checks
GRACE_PERIOD=300    # seconds to wait before first check (lets sessions settle after restart)

DRY_RUN=false

# ---------------------------------------------------------------------------
# Parse command-line arguments
# ---------------------------------------------------------------------------

ACTION="${1:-}"
shift || true

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

# Compact log line for watchdog checks (keeps the log small)
wlog() {
    echo "[$(timestamp)] WATCHDOG: $1" >> "$LOG_FILE"
}

# Cross-platform helper: get elapsed time in seconds for a PID.
# Linux has ps -o etimes= (seconds directly). macOS only has ps -o etime=
# which returns [[DD-]HH:]MM:SS format that we need to parse.
get_elapsed_seconds() {
    local pid="$1"

    # Try Linux-style etimes first (returns seconds directly)
    local seconds
    seconds=$(ps -o etimes= -p "$pid" 2>/dev/null | tr -d ' ')
    if [[ -n "$seconds" && "$seconds" =~ ^[0-9]+$ ]]; then
        echo "$seconds"
        return
    fi

    # Fall back to etime format: [[DD-]HH:]MM:SS
    local etime
    etime=$(ps -o etime= -p "$pid" 2>/dev/null | tr -d ' ')
    if [[ -z "$etime" ]]; then
        echo "0"
        return
    fi

    local days=0 hours=0 mins=0 secs=0
    # Split off days if present (format: DD-HH:MM:SS)
    if [[ "$etime" == *-* ]]; then
        days="${etime%%-*}"
        etime="${etime#*-}"
    fi
    # Split remaining HH:MM:SS or MM:SS or SS
    IFS=: read -ra parts <<< "$etime"
    case ${#parts[@]} in
        3) hours="${parts[0]}"; mins="${parts[1]}"; secs="${parts[2]}" ;;
        2) mins="${parts[0]}"; secs="${parts[1]}" ;;
        1) secs="${parts[0]}" ;;
    esac
    # Strip leading zeros to avoid octal interpretation
    days=$((10#$days)) hours=$((10#$hours)) mins=$((10#$mins)) secs=$((10#$secs))
    echo $(( days*86400 + hours*3600 + mins*60 + secs ))
}

# All OpenClaw process patterns in one place
OPENCLAW_PGREP_PATTERN="openclaw[-_ ]agent|claw-agent|openclaw-skill|clawdbot|moltbot|openclaw.*gateway"

# Find running OpenClaw Docker containers
find_openclaw_containers() {
    if ! command -v docker &>/dev/null; then
        return
    fi
    docker ps --filter "name=openclaw" --format "{{.Names}}" 2>/dev/null || true
}

# Trigger the kill script with a reason
trigger_kill() {
    local reason="$1"

    wlog "AUTO-TRIGGER: ${reason}"

    local dry_flag=""
    [[ "$DRY_RUN" == true ]] && dry_flag="--dry-run"

    "${SCRIPT_DIR}/kill.sh" \
        --trigger-source "watchdog" \
        --trigger-method "auto" \
        $dry_flag

    # Send the specific watchdog alert message
    local prefix=""
    [[ "$DRY_RUN" == true ]] && prefix="[DRY-RUN] "

    local alert="${prefix}🔴 DeadClaw auto-triggered. Reason: ${reason}. All processes stopped. Check deadclaw.log."

    if command -v openclaw &>/dev/null; then
        openclaw message broadcast --text "${alert}" 2>/dev/null || true
    fi
    echo "$alert"
}

# ---------------------------------------------------------------------------
# Check 1: Runaway loops — agents running longer than the max threshold
# ---------------------------------------------------------------------------

check_runtime() {
    local max_seconds=$((MAX_RUNTIME_MIN * 60))

    # Check native OpenClaw agent processes
    while IFS= read -r pid; do
        [[ -n "$pid" ]] || continue

        local elapsed
        elapsed=$(get_elapsed_seconds "$pid")

        if [[ "$elapsed" -gt "$max_seconds" ]]; then
            local cmd
            cmd=$(ps -o comm= -p "$pid" 2>/dev/null || echo "unknown")
            local runtime_min=$((elapsed / 60))
            trigger_kill "agent loop exceeded ${MAX_RUNTIME_MIN}min threshold (PID ${pid}, ${cmd}, running for ${runtime_min}min)"
            return 1
        fi
    done < <(pgrep -f "${OPENCLAW_PGREP_PATTERN}" 2>/dev/null || true)

    # Check Docker container sessions
    local containers
    containers=$(find_openclaw_containers)
    if [[ -n "$containers" ]]; then
        while IFS= read -r container; do
            [[ -n "$container" ]] || continue

            # Get session ages from inside the container via openclaw status
            # Parse the sessions table for age values like "27m ago", "2h ago"
            local session_info
            session_info=$(docker exec "$container" openclaw status 2>/dev/null || true)

            # Extract session age lines — look for patterns like "27m ago" or "2h ago"
            local ages
            ages=$(echo "$session_info" | grep -oE '[0-9]+[hm] +ago' 2>/dev/null || true)

            while IFS= read -r age_str; do
                [[ -n "$age_str" ]] || continue
                local age_min=0
                if [[ "$age_str" =~ ^([0-9]+)h ]]; then
                    age_min=$(( ${BASH_REMATCH[1]} * 60 ))
                elif [[ "$age_str" =~ ^([0-9]+)m ]]; then
                    age_min=${BASH_REMATCH[1]}
                fi

                if [[ "$age_min" -gt "$MAX_RUNTIME_MIN" ]]; then
                    trigger_kill "agent session in container ${container} exceeded ${MAX_RUNTIME_MIN}min threshold (running for ${age_min}min)"
                    return 1
                fi
            done <<< "$ages"
        done <<< "$containers"
    fi

    return 0
}

# ---------------------------------------------------------------------------
# Check 2: Token burn — excessive token spend in a short window
# ---------------------------------------------------------------------------

check_token_spend() {
    local token_log="${OPENCLAW_WORKSPACE:-/tmp}/.openclaw/metrics/tokens.log"

    # In Docker mode, try to get token info from containers
    if [[ ! -f "$token_log" ]]; then
        local containers
        containers=$(find_openclaw_containers)
        if [[ -n "$containers" ]]; then
            while IFS= read -r container; do
                [[ -n "$container" ]] || continue
                # Try to get token spend from the container's openclaw status
                local status_output
                status_output=$(docker exec "$container" openclaw status 2>/dev/null || true)
                # Look for token info like "0.0k/400k (0%)" in the status output
                local token_match
                token_match=$(echo "$status_output" | grep -oE '[0-9.]+k/[0-9.]+k *\([0-9]+%\)' 2>/dev/null | head -1 || true)
                if [[ -n "$token_match" ]]; then
                    # Extract used tokens (the first number before /)
                    local used_k
                    used_k=$(echo "$token_match" | grep -oE '^[0-9.]+' || echo "0")
                    # Convert k to actual tokens (rough)
                    local used_tokens
                    used_tokens=$(echo "$used_k * 1000" | bc 2>/dev/null || echo "0")
                    used_tokens=${used_tokens%.*}  # truncate decimal
                    if [[ "$used_tokens" -gt "$MAX_TOKENS" ]]; then
                        trigger_kill "token spend exceeded ${MAX_TOKENS} tokens in container ${container} (actual: ~${used_tokens} tokens)"
                        return 1
                    fi
                fi
            done <<< "$containers"
        fi
        return 0
    fi

    # If the token log doesn't exist and no Docker, skip silently
    [[ -f "$token_log" ]] || return 0

    local window_seconds=$((TOKEN_WINDOW_MIN * 60))
    local cutoff
    cutoff=$(date -u -d "${window_seconds} seconds ago" +%s 2>/dev/null || \
             date -u -v-${window_seconds}S +%s 2>/dev/null || echo "0")

    # Token log format expected: TIMESTAMP TOKENS_USED
    # Sum up tokens used within the window
    local total_tokens=0
    while IFS=' ' read -r ts tokens; do
        [[ -n "$ts" && -n "$tokens" ]] || continue
        local entry_epoch
        entry_epoch=$(date -u -d "$ts" +%s 2>/dev/null || date -u -jf "%Y-%m-%dT%H:%M:%SZ" "$ts" +%s 2>/dev/null || echo "0")
        if [[ "$entry_epoch" -ge "$cutoff" ]]; then
            total_tokens=$((total_tokens + tokens))
        fi
    done < "$token_log"

    if [[ "$total_tokens" -gt "$MAX_TOKENS" ]]; then
        trigger_kill "token spend exceeded ${MAX_TOKENS} tokens in ${TOKEN_WINDOW_MIN}min window (actual: ${total_tokens} tokens)"
        return 1
    fi

    return 0
}

# ---------------------------------------------------------------------------
# Check 3: Unauthorized network calls — connections to non-whitelisted domains
# ---------------------------------------------------------------------------

check_network() {
    # Skip if no whitelist file exists (user hasn't configured network restrictions)
    [[ -f "$WHITELIST_FILE" ]] || return 0

    # Get current outbound connections from OpenClaw agent processes (native)
    local agent_pids
    agent_pids=$(pgrep -f "${OPENCLAW_PGREP_PATTERN}" 2>/dev/null || true)

    # In Docker mode, also check container network connections
    if [[ -z "$agent_pids" ]]; then
        local containers
        containers=$(find_openclaw_containers)
        if [[ -n "$containers" ]]; then
            # For Docker containers, we check from the host using docker's network
            while IFS= read -r container; do
                [[ -n "$container" ]] || continue
                local container_pid
                container_pid=$(docker inspect --format '{{.State.Pid}}' "$container" 2>/dev/null || true)
                [[ -n "$container_pid" && "$container_pid" != "0" ]] && agent_pids="${agent_pids}${agent_pids:+$'\n'}${container_pid}"
            done <<< "$containers"
        fi
    fi

    [[ -n "$agent_pids" ]] || return 0

    # Load whitelist into an associative array for fast lookup
    declare -A allowed_domains
    while IFS= read -r domain; do
        domain=$(echo "$domain" | tr -d '[:space:]')
        [[ -n "$domain" && "$domain" != \#* ]] && allowed_domains["$domain"]=1
    done < "$WHITELIST_FILE"

    # Check each agent process for outbound connections
    while IFS= read -r pid; do
        [[ -n "$pid" ]] || continue

        # Use lsof or ss to find network connections for this PID
        local connections
        connections=$(lsof -i -a -p "$pid" -n 2>/dev/null | grep "ESTABLISHED" || true)

        while IFS= read -r conn; do
            [[ -n "$conn" ]] || continue

            # Extract the remote address/hostname
            local remote
            remote=$(echo "$conn" | awk '{print $9}' | cut -d':' -f1 | sed 's/->/ /g' | awk '{print $NF}')
            [[ -n "$remote" ]] || continue

            # Try reverse DNS lookup
            local hostname
            hostname=$(host "$remote" 2>/dev/null | awk '/domain name pointer/ {print $NF}' | sed 's/\.$//' || echo "$remote")

            # Check if this domain (or any parent domain) is whitelisted
            local is_allowed=false
            for allowed in "${!allowed_domains[@]}"; do
                if [[ "$hostname" == *"$allowed"* || "$remote" == *"$allowed"* ]]; then
                    is_allowed=true
                    break
                fi
            done

            if [[ "$is_allowed" == false ]]; then
                trigger_kill "unauthorized outbound network call to ${hostname} (${remote}) from PID ${pid}"
                return 1
            fi
        done <<< "$connections"
    done <<< "$agent_pids"

    return 0
}

# ---------------------------------------------------------------------------
# Check 4: Sandbox escape — file writes outside the designated workspace
# ---------------------------------------------------------------------------

check_file_writes() {
    # Skip if no workspace is configured
    [[ -n "$WORKSPACE" ]] || return 0

    local agent_pids
    agent_pids=$(pgrep -f "${OPENCLAW_PGREP_PATTERN}" 2>/dev/null || true)
    [[ -n "$agent_pids" ]] || return 0

    # Use lsof to check for open file descriptors in write mode outside workspace
    while IFS= read -r pid; do
        [[ -n "$pid" ]] || continue

        # Find files opened for writing by this process
        local write_files
        write_files=$(lsof -p "$pid" 2>/dev/null | awk '$4 ~ /[0-9]+w/' | awk '{print $9}' || true)

        while IFS= read -r filepath; do
            [[ -n "$filepath" ]] || continue

            # Resolve to absolute path
            local abs_path
            abs_path=$(realpath "$filepath" 2>/dev/null || echo "$filepath")

            # Check if the file is outside the workspace (allow /tmp and /dev)
            if [[ "$abs_path" != "${WORKSPACE}"* && \
                  "$abs_path" != /tmp* && \
                  "$abs_path" != /dev* && \
                  "$abs_path" != /proc* ]]; then
                trigger_kill "process PID ${pid} writing outside workspace: ${abs_path} (workspace: ${WORKSPACE})"
                return 1
            fi
        done <<< "$write_files"
    done <<< "$agent_pids"

    return 0
}

# ---------------------------------------------------------------------------
# Daemon management
# ---------------------------------------------------------------------------

start_watchdog() {
    # Check if already running
    if [[ -f "$PID_FILE" ]]; then
        local existing_pid
        existing_pid=$(cat "$PID_FILE")
        if kill -0 "$existing_pid" 2>/dev/null; then
            echo "Watchdog is already running (PID ${existing_pid})."
            exit 0
        else
            # Stale PID file — clean it up
            rm -f "$PID_FILE"
        fi
    fi

    echo "Starting DeadClaw watchdog..."
    wlog "Watchdog starting. Check interval: ${CHECK_INTERVAL}s. Dry run: ${DRY_RUN}"
    wlog "Thresholds: runtime=${MAX_RUNTIME_MIN}min, tokens=${MAX_TOKENS}/${TOKEN_WINDOW_MIN}min"

    # Fork into the background
    (
        # Clean up PID file on exit (TERM from kill command, INT from Ctrl-C)
        trap 'wlog "Watchdog stopped by signal."; rm -f "$PID_FILE"; exit 0' TERM INT

        # Grace period: wait before first check to let sessions settle after restart.
        # This prevents false triggers on pre-existing sessions that were restored.
        wlog "Grace period: waiting ${GRACE_PERIOD}s before first check..."
        sleep "$GRACE_PERIOD" &
        wait $! 2>/dev/null || true

        while true; do
            # Run all checks. If any check triggers a kill, the watchdog stops
            # (because kill.sh stops the watchdog as part of its cleanup).
            wlog "CHECK: scanning..."

            check_runtime || { wlog "Watchdog stopping after auto-trigger."; exit 0; }
            check_token_spend || { wlog "Watchdog stopping after auto-trigger."; exit 0; }
            check_network || { wlog "Watchdog stopping after auto-trigger."; exit 0; }
            check_file_writes || { wlog "Watchdog stopping after auto-trigger."; exit 0; }

            wlog "CHECK: all clear"

            # Sleep in background + wait makes the loop interruptible by signals.
            # A plain 'sleep 60' blocks signal delivery until it completes.
            sleep "$CHECK_INTERVAL" &
            wait $! 2>/dev/null || true
        done
    ) &

    local daemon_pid=$!
    echo "$daemon_pid" > "$PID_FILE"
    echo "Watchdog started (PID ${daemon_pid}). Logging to ${LOG_FILE}."
}

stop_watchdog() {
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            wlog "Watchdog stopped (PID ${pid})"
            echo "Watchdog stopped (PID ${pid})."
        else
            echo "Watchdog was not running (stale PID file)."
        fi
        rm -f "$PID_FILE"
    else
        echo "Watchdog is not running (no PID file found)."
    fi
}

watchdog_status() {
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo "Watchdog is running (PID ${pid})."
            echo "  Check interval: ${CHECK_INTERVAL}s"
            echo "  Max runtime: ${MAX_RUNTIME_MIN}min"
            echo "  Max tokens: ${MAX_TOKENS} / ${TOKEN_WINDOW_MIN}min"
            echo "  Dry run: ${DRY_RUN}"
            return 0
        else
            echo "Watchdog is not running (stale PID file)."
            rm -f "$PID_FILE"
            return 1
        fi
    else
        echo "Watchdog is not running."
        return 1
    fi
}

# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

case "${ACTION}" in
    start)
        start_watchdog
        ;;
    stop)
        stop_watchdog
        ;;
    status)
        watchdog_status
        ;;
    *)
        echo "Usage: watchdog.sh {start|stop|status} [--dry-run]"
        exit 1
        ;;
esac
