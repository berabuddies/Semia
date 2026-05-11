#!/bin/bash

# claw-roam - OpenClaw Workspace Sync Tool
# Usage: claw-roam [push|pull|status|merge-from|sync] [options]

set -e

WORKSPACE_DIR="${HOME}/.openclaw/workspace"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$WORKSPACE_DIR"

show_help() {
    cat << EOF
Claw Roam - Sync OpenClaw workspace between machines

Usage:
    claw-roam push [message]         Commit+push current branch
    claw-roam pull                   Pull latest for current branch
    claw-roam status                 Check sync status
    claw-roam merge-from <branch>    Merge another branch into current branch
    claw-roam sync                   Full sync: push local, merge main, push to main
    claw-roam help                   Show this help

Examples:
    claw-roam push "before travel"
    claw-roam pull
    claw-roam status
    claw-roam merge-from local
    claw-roam sync
EOF
}

cmd_push() {
    local message="${1:-auto: $(date '+%Y-%m-%d %H:%M:%S')}"
    
    # Check if git repo exists
    if [ ! -d ".git" ]; then
        echo "❌ Not a git repository. Run 'git init' first."
        exit 1
    fi
    
    # Check if there are changes
    if [ -z "$(git status --porcelain)" ]; then
        echo "✅ No changes to push (already up to date)"
        git log -1 --oneline
        exit 0
    fi
    
    echo "📦 Adding changes..."
    git add -A
    
    echo "💾 Committing: $message"
    git commit -m "$message"
    
    echo "🚀 Pushing to remote..."
    git push
    
    echo "✅ Push complete!"
    git log -1 --oneline
}

cmd_pull() {
    # Check if git repo exists
    if [ ! -d ".git" ]; then
        echo "❌ Not a git repository. Run 'git init' first."
        exit 1
    fi
    
    echo "📥 Fetching from remote..."
    git fetch origin
    
    local local_commit=$(git rev-parse HEAD)
    local remote_commit=$(git rev-parse origin/$(git branch --show-current))
    
    if [ "$local_commit" = "$remote_commit" ]; then
        echo "✅ Already up to date"
        git log -1 --oneline
        exit 0
    fi
    
    echo "🔄 Pulling changes..."
    git pull origin $(git branch --show-current)
    
    echo "✅ Pull complete!"
    git log -1 --oneline
    
    # If on VPS, suggest restarting gateway
    if [ -n "$OPENCLAW_VPS" ] || [ -f "/etc/openclaw/vps" ]; then
        echo ""
        echo "💡 VPS detected. Restart OpenClaw gateway to apply changes:"
        echo "   openclaw gateway restart"
    fi
}

cmd_merge_from() {
    local from_branch="${1:-}"
    [ -n "$from_branch" ] || { echo "❌ missing branch name"; echo "   usage: claw-roam merge-from <branch>"; exit 1; }

    if [ ! -d ".git" ]; then
        echo "❌ Not a git repository."
        exit 1
    fi

    local cur_branch
    cur_branch=$(git branch --show-current)
    echo "🔀 Merging from: $from_branch -> $cur_branch"

    echo "📥 Fetching..."
    git fetch origin --prune

    echo "🔧 Merge..."
    git merge "origin/${from_branch}" -m "merge: ${from_branch} -> ${cur_branch}" || {
      echo "❌ Merge failed (likely conflicts). Resolve them, then run:"
      echo "   git status"
      echo "   git add -A && git commit"
      exit 1
    }

    echo "✅ Merge complete."
    git log -1 --oneline
}

cmd_status() {
    # Check if git repo exists
    if [ ! -d ".git" ]; then
        echo "❌ Not a git repository"
        echo ""
        echo "Setup steps:"
        echo "   cd ~/.openclaw/workspace"
        echo "   git init"
        echo "   git remote add origin <your-repo-url>"
        echo "   git add -A && git commit -m 'initial' && git push -u origin main"
        exit 1
    fi

    echo "📍 Current branch: $(git branch --show-current)"
    echo "🔖 Latest commit:  $(git log -1 --oneline)"
    echo ""

    # Check for unpushed commits
    local unpushed=$(git log --branches --not --remotes --oneline 2>/dev/null || echo "")
    if [ -n "$unpushed" ]; then
        echo "⚠️  Unpushed commits:"
        echo "$unpushed" | head -5
        local count=$(echo "$unpushed" | wc -l | tr -d ' ')
        [ "$count" -gt 5 ] && echo "   ... and $((count - 5)) more"
        echo ""
        echo "💡 Run: claw-roam push"
    else
        echo "✅ All commits pushed"
    fi

    # Check for uncommitted changes
    if [ -n "$(git status --porcelain)" ]; then
        echo ""
        echo "📝 Uncommitted changes:"
        git status --short
        echo ""
        echo "💡 Run: claw-roam push"
    else
        echo "✅ No uncommitted changes"
    fi

    # Check remote status
    git fetch origin --quiet 2>/dev/null || true
    local behind=$(git rev-list --count HEAD..origin/$(git branch --show-current) 2>/dev/null || echo "0")
    if [ "$behind" -gt 0 ]; then
        echo ""
        echo "🔄 Remote is $behind commit(s) ahead"
        echo "💡 Run: claw-roam pull"
    fi
}

cmd_sync() {
    local current_branch
    current_branch=$(git branch --show-current)
    
    echo "🔄 Full sync workflow: $current_branch -> main"
    echo ""
    
    # Step 1: Commit and push current branch
    echo "Step 1: Commit and push current branch ($current_branch)"
    if [ -n "$(git status --porcelain)" ]; then
        git add -A
        git commit -m "sync: auto-commit on $current_branch"
        echo "✅ Committed changes"
    else
        echo "ℹ️ No changes to commit"
    fi
    
    echo "🚀 Pushing $current_branch..."
    git push origin "$current_branch"
    echo "✅ Pushed $current_branch"
    echo ""
    
    # Step 2: Merge main into current branch
    echo "Step 2: Merge main into $current_branch"
    git fetch origin main
    if git merge-base --is-ancestor origin/main HEAD; then
        echo "ℹ️ Already up to date with main"
    else
        git merge origin/main -m "sync: merge main -> $current_branch" || {
            echo "❌ Merge failed. Resolve conflicts and run: git add -A && git commit"
            exit 1
        }
        echo "✅ Merged main into $current_branch"
    fi
    echo ""
    
    # Step 3: Merge current branch into main and push
    echo "Step 3: Push to main branch"
    git fetch origin main
    local main_branch="main"
    
    # Check if main exists locally
    if ! git show-ref --verify --quiet refs/heads/main; then
        # Check if master exists
        if git show-ref --verify --quiet refs/heads/master; then
            main_branch="master"
        else
            git checkout -b main origin/main
            main_branch="main"
        fi
    fi
    
    # Stash any uncommitted changes before switching
    local had_stash=false
    if [ -n "$(git status --porcelain)" ]; then
        git stash push -m "sync-stash"
        had_stash=true
    fi
    
    git checkout "$main_branch"
    
    # Pull latest main first
    git pull origin "$main_branch" || true
    
    # Merge current branch
    git merge "$current_branch" -m "sync: merge $current_branch -> main"
    
    # Push main
    git push origin "$main_branch"
    echo "✅ Pushed to main"
    
    # Switch back to original branch
    git checkout "$current_branch"
    
    # Restore stash if we had one
    if [ "$had_stash" = true ]; then
        git stash pop || true
    fi
    
    echo ""
    echo "🎉 Sync complete!"
    echo "   $current_branch: $(git log -1 --oneline)"
    echo "   main: $(git log origin/main -1 --oneline)"
}

# Main
case "${1:-help}" in
    push)
        shift
        cmd_push "$@"
        ;;
    pull)
        cmd_pull
        ;;
    status)
        cmd_status
        ;;
    merge-from)
        shift
        cmd_merge_from "$@"
        ;;
    sync)
        cmd_sync
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
