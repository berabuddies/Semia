#!/usr/bin/env bash
# ============================================================================
# DeadClaw — status.sh
# Health report script. Sends a plain-English summary of what's running,
# how long it's been running, current token spend rate, and watchdog status.
#
# Supports both native and Docker-based OpenClaw installs.
#
# Usage:
#   ./status.sh               # Print status to stdout
#   ./status.sh --dry-run     # Same behavior (status is read-only)
#   ./status.sh --json        # Output as JSON for programmatic use
#
# Trigger: user sends "status" to any connected OpenClaw channel.
# ============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="${SKILL_DIR}/deadclaw-watchdog.pid"

OUTPUT_JSON=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --json)    OUTPUT_JSON=true; shift ;;
        --dry-run) shift ;;  # status is already read-only
        *)         shift ;;
    esac
done

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Cross-platform: get elapsed time in seconds for a PID.
get_elapsed_seconds() {
    local pid="$1"
    local seconds
    seconds=$(ps -o etimes= -p "$pid" 2>/dev/null | tr -d ' ')
    if [[ -n "$seconds" && "$seconds" =~ ^[0-9]+$ ]]; then
        echo "$seconds"
        return
    fi
    local etime
    etime=$(ps -o etime= -p "$pid" 2>/dev/null | tr -d ' ')
    if [[ -z "$etime" ]]; then
        echo "0"
        return
    fi
    local days=0 hours=0 mins=0 secs=0
    if [[ "$etime" == *-* ]]; then
        days="${etime%%-*}"
        etime="${etime#*-}"
    fi
    IFS=: read -ra parts <<< "$etime"
    case ${#parts[@]} in
        3) hours="${parts[0]}"; mins="${parts[1]}"; secs="${parts[2]}" ;;
        2) mins="${parts[0]}"; secs="${parts[1]}" ;;
        1) secs="${parts[0]}" ;;
    esac
    days=$((10#$days)) hours=$((10#$hours)) mins=$((10#$mins)) secs=$((10#$secs))
    echo $(( days*86400 + hours*3600 + mins*60 + secs ))
}

# Format seconds into human-readable uptime
format_uptime() {
    local elapsed="$1"
    if [[ "$elapsed" -ge 86400 ]]; then
        echo "$((elapsed / 86400))d $((elapsed % 86400 / 3600))h"
    elif [[ "$elapsed" -ge 3600 ]]; then
        echo "$((elapsed / 3600))h $((elapsed % 3600 / 60))m"
    elif [[ "$elapsed" -ge 60 ]]; then
        echo "$((elapsed / 60))m $((elapsed % 60))s"
    else
        echo "${elapsed}s"
    fi
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

# ---------------------------------------------------------------------------
# Gather information — Docker mode
# ---------------------------------------------------------------------------

gather_docker_status() {
    local containers
    containers=$(find_openclaw_containers)

    if [[ -z "$containers" ]]; then
        return 1
    fi

    # List containers with uptime
    echo ""
    echo "DeadClaw Status Report"
    echo "======================"
    echo ""

    local container_count=0
    while IFS= read -r container; do
        [[ -n "$container" ]] || continue
        container_count=$((container_count + 1))

        local status uptime_str
        status=$(docker inspect --format '{{.State.Status}}' "$container" 2>/dev/null || echo "unknown")
        uptime_str=$(docker inspect --format '{{.State.StartedAt}}' "$container" 2>/dev/null || echo "unknown")

        echo "Docker container: ${container}"
        echo "  Status: ${status}"
        echo "  Started: ${uptime_str}"
        echo ""

        # Get detailed status from inside the container
        local oc_status
        oc_status=$(docker exec "$container" openclaw status --all 2>/dev/null || echo "(could not reach openclaw inside container)")
        echo "  OpenClaw status:"
        echo "$oc_status" | while IFS= read -r line; do
            echo "    $line"
        done
        echo ""
    done <<< "$containers"

    echo "Containers: ${container_count} running"
    echo ""

    # Also check for native processes on the host
    local native_pids
    native_pids=$(pgrep -f "${OPENCLAW_PGREP_PATTERN}" 2>/dev/null || true)
    if [[ -n "$native_pids" ]]; then
        local native_count
        native_count=$(echo "$native_pids" | wc -l | tr -d ' ')
        echo "Host processes: ${native_count} running"
        while IFS= read -r pid; do
            [[ -n "$pid" ]] || continue
            local pname elapsed uptime
            pname=$(ps -o comm= -p "$pid" 2>/dev/null || echo "unknown")
            elapsed=$(get_elapsed_seconds "$pid")
            uptime=$(format_uptime "$elapsed")
            echo "  - ${pname} (PID ${pid}) — up ${uptime}"
        done <<< "$native_pids"
        echo ""
    fi

    # Watchdog status
    if [[ -f "$PID_FILE" ]]; then
        local wpid
        wpid=$(cat "$PID_FILE" 2>/dev/null)
        if kill -0 "$wpid" 2>/dev/null; then
            echo "Watchdog: Active (PID ${wpid})"
        else
            echo "Watchdog: Not running (stale PID file)"
        fi
    else
        echo "Watchdog: Not running"
    fi

    echo ""
    return 0
}

# ---------------------------------------------------------------------------
# Gather information — Native mode (no Docker)
# ---------------------------------------------------------------------------

gather_native_status() {
    declare -a agent_names=()
    declare -a agent_pids=()
    declare -a agent_uptimes=()

    while IFS= read -r pid; do
        [[ -n "$pid" ]] || continue
        agent_pids+=("$pid")
        local_name=$(ps -o comm= -p "$pid" 2>/dev/null || echo "unknown")
        agent_names+=("$local_name")
        local_elapsed=$(get_elapsed_seconds "$pid")
        agent_uptimes+=("$(format_uptime "$local_elapsed")")
    done < <(pgrep -f "${OPENCLAW_PGREP_PATTERN}" 2>/dev/null || true)

    local agent_count=${#agent_pids[@]}

    # Token spend rate
    local token_rate="unknown"
    local token_total="unknown"
    local token_log="${OPENCLAW_WORKSPACE:-/tmp}/.openclaw/metrics/tokens.log"
    if [[ -f "$token_log" ]]; then
        local_total=$(tail -50 "$token_log" 2>/dev/null | awk '{sum += $2} END {print sum+0}' || echo "0")
        token_total="$local_total"
        token_rate="~${local_total} tokens/10min"
    fi

    # Watchdog status
    local watchdog_running=false
    local watchdog_pid=""
    if [[ -f "$PID_FILE" ]]; then
        watchdog_pid=$(cat "$PID_FILE" 2>/dev/null)
        if kill -0 "$watchdog_pid" 2>/dev/null; then
            watchdog_running=true
        fi
    fi

    # Warnings
    local warnings=()
    local max_runtime=${DEADCLAW_MAX_RUNTIME_MIN:-30}
    local max_tokens=${DEADCLAW_MAX_TOKENS:-50000}

    for i in "${!agent_pids[@]}"; do
        local_elapsed=$(get_elapsed_seconds "${agent_pids[$i]}")
        local_threshold_sec=$((max_runtime * 60))
        local_warning_sec=$((local_threshold_sec * 80 / 100))
        if [[ "$local_elapsed" -ge "$local_warning_sec" ]]; then
            warnings+=("Agent ${agent_names[$i]} (PID ${agent_pids[$i]}) has been running ${agent_uptimes[$i]} — approaching ${max_runtime}min kill threshold")
        fi
    done

    if [[ "$token_total" != "unknown" && "$token_total" -ge $((max_tokens * 80 / 100)) ]]; then
        warnings+=("Token spend is at ${token_total} — approaching ${max_tokens} kill threshold")
    fi

    if [[ "$OUTPUT_JSON" == true ]]; then
        local agents_json="["
        for i in "${!agent_pids[@]}"; do
            [[ $i -gt 0 ]] && agents_json+=","
            agents_json+="{\"name\":\"${agent_names[$i]}\",\"pid\":${agent_pids[$i]},\"uptime\":\"${agent_uptimes[$i]}\"}"
        done
        agents_json+="]"

        local warnings_json="["
        for i in "${!warnings[@]}"; do
            [[ $i -gt 0 ]] && warnings_json+=","
            warnings_json+="\"${warnings[$i]}\""
        done
        warnings_json+="]"

        cat <<EOF
{
  "agents_running": ${agent_count},
  "agents": ${agents_json},
  "token_rate": "${token_rate}",
  "watchdog_active": ${watchdog_running},
  "watchdog_pid": "${watchdog_pid}",
  "warnings": ${warnings_json}
}
EOF
    else
        echo ""
        echo "DeadClaw Status Report"
        echo "======================"
        echo ""

        if [[ "$agent_count" -eq 0 ]]; then
            echo "Agents: None running."
        else
            echo "Agents: ${agent_count} running"
            for i in "${!agent_pids[@]}"; do
                echo "  - ${agent_names[$i]} (PID ${agent_pids[$i]}) — up ${agent_uptimes[$i]}"
            done
        fi

        echo ""
        echo "Token spend: ${token_rate}"
        echo ""

        if [[ "$watchdog_running" == true ]]; then
            echo "Watchdog: Active (PID ${watchdog_pid})"
        else
            echo "Watchdog: Not running"
        fi

        if [[ ${#warnings[@]} -gt 0 ]]; then
            echo ""
            echo "Warnings:"
            for w in "${warnings[@]}"; do
                echo "  ! ${w}"
            done
        fi

        echo ""
    fi
}

# ---------------------------------------------------------------------------
# Main — detect Docker vs native and gather status
# ---------------------------------------------------------------------------

containers=$(find_openclaw_containers)
if [[ -n "$containers" ]]; then
    gather_docker_status
else
    gather_native_status
fi
