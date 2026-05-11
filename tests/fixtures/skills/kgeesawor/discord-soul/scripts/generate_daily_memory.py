#!/usr/bin/env python3
"""
Generate RICH daily memory files for a Discord Community Agent.
Includes FULL message content, not just summaries.

Usage: 
    python generate_daily_memory.py YYYY-MM-DD --db ./discord.sqlite --out ./memory/
    python generate_daily_memory.py --all --db ./discord.sqlite --out ./memory/

Environment variables (alternative to flags):
    DISCORD_SOUL_DB      Path to SQLite database
    DISCORD_SOUL_MEMORY  Path to memory output directory
"""

import sqlite3
import sys
import os
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter


def get_db_path(args):
    """Get database path from args or environment."""
    if args.db:
        return Path(args.db)
    if os.environ.get('DISCORD_SOUL_DB'):
        return Path(os.environ['DISCORD_SOUL_DB'])
    print("Error: No database specified. Use --db or set DISCORD_SOUL_DB")
    sys.exit(1)


def get_memory_path(args):
    """Get memory output path from args or environment."""
    if args.out:
        return Path(args.out)
    if os.environ.get('DISCORD_SOUL_MEMORY'):
        return Path(os.environ['DISCORD_SOUL_MEMORY'])
    print("Error: No output path specified. Use --out or set DISCORD_SOUL_MEMORY")
    sys.exit(1)


def get_day_data(db_path: Path, date_str: str) -> dict:
    """Query all rich data for a specific day."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Parse date
    date = datetime.strptime(date_str, "%Y-%m-%d")
    
    # Get ALL messages for the day with full content
    cur.execute("""
        SELECT 
            id, content, author_id, author_name, author_nickname, author_color,
            channel_id, channel_name, channel_category, timestamp, 
            reactions_count, reply_to, message_type, is_pinned,
            attachments_count, embeds_count, mentions_count
        FROM messages
        WHERE date(timestamp) = ?
        ORDER BY timestamp
    """, (date_str,))
    messages = [dict(row) for row in cur.fetchall()]
    
    # Get reactions for this day (emoji breakdown)
    cur.execute("""
        SELECT r.emoji, r.emoji_name, SUM(r.count) as total
        FROM reactions r
        JOIN messages m ON r.message_id = m.id
        WHERE date(m.timestamp) = ?
        GROUP BY r.emoji
        ORDER BY total DESC
        LIMIT 10
    """, (date_str,))
    top_reactions = [(row[0], row[2]) for row in cur.fetchall()]
    
    # Get reactions per message for annotation
    cur.execute("""
        SELECT r.message_id, GROUP_CONCAT(r.emoji || '(' || r.count || ')', ' ') as reactions
        FROM reactions r
        JOIN messages m ON r.message_id = m.id
        WHERE date(m.timestamp) = ?
        GROUP BY r.message_id
    """, (date_str,))
    message_reactions = {row[0]: row[1] for row in cur.fetchall()}
    
    # Get roles active today
    cur.execute("""
        SELECT DISTINCT role_name, role_color, COUNT(DISTINCT author_id) as holders
        FROM roles
        WHERE first_seen_date <= ?
        GROUP BY role_name
        ORDER BY role_position DESC
    """, (date_str,))
    active_roles = [(row[0], row[2]) for row in cur.fetchall()]
    
    # Get new roles first seen today
    cur.execute("""
        SELECT author_name, role_name
        FROM roles
        WHERE first_seen_date = ?
    """, (date_str,))
    new_roles = [(row[0], row[1]) for row in cur.fetchall()]
    
    # Get channels active today
    cur.execute("""
        SELECT channel_name, channel_category, COUNT(*) as msg_count
        FROM messages
        WHERE date(timestamp) = ?
        GROUP BY channel_id
        ORDER BY msg_count DESC
    """, (date_str,))
    channels = [(row[0], row[1], row[2]) for row in cur.fetchall()]
    
    # Get new channels first seen today
    cur.execute("""
        SELECT name, category_name
        FROM channels
        WHERE first_seen_date = ?
    """, (date_str,))
    new_channels = [(row[0], row[1]) for row in cur.fetchall()]
    
    # Get mentions
    cur.execute("""
        SELECT mentioned_name, COUNT(*) as times
        FROM mentions mn
        JOIN messages m ON mn.message_id = m.id
        WHERE date(m.timestamp) = ?
        GROUP BY mentioned_id
        ORDER BY times DESC
        LIMIT 10
    """, (date_str,))
    top_mentioned = [(row[0], row[1]) for row in cur.fetchall()]
    
    conn.close()
    
    # Calculate derived metrics
    authors = set(m['author_id'] for m in messages)
    author_names = Counter(m['author_name'] or m['author_nickname'] for m in messages)
    
    return {
        'date': date_str,
        'day_of_week': date.strftime('%A'),
        'messages': messages,
        'message_reactions': message_reactions,
        'message_count': len(messages),
        'author_count': len(authors),
        'channel_count': len(set(m['channel_id'] for m in messages)),
        'total_reactions': sum(m['reactions_count'] or 0 for m in messages),
        'top_channels': channels[:10],
        'new_channels': new_channels,
        'top_authors': author_names.most_common(10),
        'top_reactions': top_reactions,
        'active_roles': active_roles,
        'new_roles': new_roles,
        'top_mentioned': top_mentioned,
    }


def generate_memory_file(data: dict) -> str:
    """Generate the rich markdown memory file with FULL message content."""
    lines = [
        f"# {data['date']} ({data['day_of_week']})",
        "",
        "## Quick Stats",
        f"- **Messages:** {data['message_count']}",
        f"- **Active authors:** {data['author_count']}",
        f"- **Channels active:** {data['channel_count']}",
        f"- **Total reactions:** {data['total_reactions']}",
    ]
    
    # Reaction breakdown
    if data['top_reactions']:
        lines.extend(["", "## Emotional Pulse"])
        reaction_str = " | ".join([f"{emoji} ({count})" for emoji, count in data['top_reactions'][:7]])
        lines.append(f"{reaction_str}")
    
    # New channels
    if data['new_channels']:
        lines.extend(["", "## New Channels Born Today"])
        for name, category in data['new_channels'][:10]:
            lines.append(f"- #{name} ({category})")
        if len(data['new_channels']) > 10:
            lines.append(f"- ...and {len(data['new_channels']) - 10} more")
    
    # New roles
    if data['new_roles']:
        lines.extend(["", "## New Badges Earned"])
        for author, role in data['new_roles'][:10]:
            lines.append(f"- **{author}** → {role}")
    
    # Top mentioned
    if data['top_mentioned']:
        lines.extend(["", "## Who Got Called On"])
        for name, times in data['top_mentioned'][:5]:
            lines.append(f"- @{name}: {times} mentions")
    
    # Active channels
    lines.extend(["", "## Where We Gathered"])
    for name, category, count in data['top_channels'][:7]:
        lines.append(f"- #{name}: {count} msgs")
    
    lines.extend([
        "",
        "---",
        "",
        "# Full Conversation Log",
        "",
        "*Everything that was said today, in order:*",
        ""
    ])
    
    # Group messages by channel for readability
    messages_by_channel = {}
    for msg in data['messages']:
        channel = msg['channel_name'] or 'unknown'
        if channel not in messages_by_channel:
            messages_by_channel[channel] = []
        messages_by_channel[channel].append(msg)
    
    # Output messages grouped by channel
    for channel, msgs in sorted(messages_by_channel.items(), key=lambda x: -len(x[1])):
        lines.append(f"## #{channel} ({len(msgs)} messages)")
        lines.append("")
        
        for msg in msgs:
            author = msg['author_nickname'] or msg['author_name'] or 'Unknown'
            content = msg['content'] or '[no text]'
            timestamp = msg['timestamp'].split('T')[1].split('.')[0] if msg['timestamp'] else ''
            reactions = data['message_reactions'].get(msg['id'], '')
            
            # Format the message
            lines.append(f"**[{timestamp}] {author}:**")
            
            # Handle multi-line content
            if '\n' in content:
                lines.append("```")
                lines.append(content)
                lines.append("```")
            else:
                lines.append(f"> {content}")
            
            # Add reactions if any
            if reactions:
                lines.append(f"*Reactions: {reactions}*")
            
            # Add reply indicator
            if msg['reply_to']:
                lines.append(f"*(replying to a previous message)*")
            
            lines.append("")
    
    lines.extend([
        "---",
        f"*End of {data['date']} — {data['message_count']} messages from {data['author_count']} people*"
    ])
    
    return '\n'.join(lines)


def get_date_range(db_path: Path) -> tuple:
    """Get the min and max dates from the database."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT MIN(date(timestamp)), MAX(date(timestamp)) FROM messages")
    row = cur.fetchone()
    conn.close()
    return row[0], row[1]


def main():
    parser = argparse.ArgumentParser(description='Generate daily memory files from Discord SQLite')
    parser.add_argument('date', nargs='?', help='Date (YYYY-MM-DD) or --all')
    parser.add_argument('--all', action='store_true', help='Generate for all days in database')
    parser.add_argument('--db', help='Path to SQLite database')
    parser.add_argument('--out', help='Path to memory output directory')
    args = parser.parse_args()
    
    db_path = get_db_path(args)
    memory_path = get_memory_path(args)
    
    if not db_path.exists():
        print(f"Error: Database not found: {db_path}")
        sys.exit(1)
    
    memory_path.mkdir(parents=True, exist_ok=True)
    
    if args.all or args.date == '--all':
        # Generate for all days in database
        min_date, max_date = get_date_range(db_path)
        if not min_date:
            print("No messages in database")
            sys.exit(1)
        
        start = datetime.strptime(min_date, "%Y-%m-%d")
        end = datetime.strptime(max_date, "%Y-%m-%d")
        current = start
        
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            print(f"Generating {date_str}...")
            try:
                data = get_day_data(db_path, date_str)
                if data['message_count'] > 0:
                    content = generate_memory_file(data)
                    out_path = memory_path / f"{date_str}.md"
                    out_path.write_text(content)
                    size_kb = len(content) / 1024
                    print(f"  → {data['message_count']} msgs, {size_kb:.1f}KB")
                else:
                    print(f"  → No messages")
            except Exception as e:
                print(f"  → Error: {e}")
                import traceback
                traceback.print_exc()
            current += timedelta(days=1)
    elif args.date:
        date_str = args.date
        data = get_day_data(db_path, date_str)
        content = generate_memory_file(data)
        out_path = memory_path / f"{date_str}.md"
        out_path.write_text(content)
        print(f"Generated {out_path}")
        print(f"  {data['message_count']} messages, {len(content)/1024:.1f}KB")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
