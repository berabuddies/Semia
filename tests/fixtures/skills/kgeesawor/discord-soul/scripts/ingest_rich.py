#!/usr/bin/env python3
"""
Rich ingestion script for Discord JSON exports.
Captures ALL available data for richer agent memory.

Tables created:
- messages: Full message data
- reactions: Individual emoji reactions per message
- roles: Author roles seen (with first appearance date)
- channels: Channel metadata (category, topic, creation)
- mentions: Who mentioned whom
- attachments: File attachments with details
- embeds: Link embeds and previews

Usage: python ingest_rich.py --input ./export/ --output ./discord.sqlite

Environment variables (alternative to flags):
    DISCORD_SOUL_INPUT   Path to export directory
    DISCORD_SOUL_DB      Path to output SQLite database
"""

import json
import sqlite3
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict


# Track first appearance of roles
role_first_seen = defaultdict(lambda: defaultdict(str))


def create_schema(conn):
    """Create the enriched database schema."""
    cur = conn.cursor()
    
    # Messages table (enhanced)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            channel_id TEXT,
            channel_name TEXT,
            channel_category TEXT,
            author_id TEXT,
            author_name TEXT,
            author_nickname TEXT,
            author_color TEXT,
            author_is_bot INTEGER,
            content TEXT,
            timestamp TEXT,
            timestamp_epoch INTEGER,
            message_type TEXT,
            is_pinned INTEGER,
            reply_to TEXT,
            reactions_count INTEGER,
            attachments_count INTEGER,
            embeds_count INTEGER,
            mentions_count INTEGER
        )
    """)
    
    # Reactions table (emoji breakdown)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT,
            emoji TEXT,
            emoji_name TEXT,
            count INTEGER,
            FOREIGN KEY (message_id) REFERENCES messages(id)
        )
    """)
    
    # Roles table (author roles with first seen date)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_id TEXT,
            author_name TEXT,
            role_id TEXT,
            role_name TEXT,
            role_color TEXT,
            role_position INTEGER,
            first_seen_date TEXT,
            UNIQUE(author_id, role_id)
        )
    """)
    
    # Channels table (metadata)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            id TEXT PRIMARY KEY,
            name TEXT,
            type TEXT,
            category_id TEXT,
            category_name TEXT,
            topic TEXT,
            first_seen_date TEXT
        )
    """)
    
    # Mentions table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mentions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT,
            mentioned_id TEXT,
            mentioned_name TEXT,
            mention_type TEXT,
            FOREIGN KEY (message_id) REFERENCES messages(id)
        )
    """)
    
    # Attachments table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT,
            attachment_id TEXT,
            filename TEXT,
            url TEXT,
            file_size INTEGER,
            content_type TEXT,
            FOREIGN KEY (message_id) REFERENCES messages(id)
        )
    """)
    
    # Embeds table (link previews)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS embeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT,
            embed_type TEXT,
            title TEXT,
            description TEXT,
            url TEXT,
            provider TEXT,
            FOREIGN KEY (message_id) REFERENCES messages(id)
        )
    """)
    
    # Daily stats table (for quick lookups)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_stats (
            date TEXT PRIMARY KEY,
            message_count INTEGER,
            author_count INTEGER,
            channel_count INTEGER,
            reaction_count INTEGER,
            top_emoji TEXT,
            new_members INTEGER
        )
    """)
    
    # Indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_channel ON messages(channel_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_author ON messages(author_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp_epoch)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_date ON messages(date(timestamp))")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_reactions_message ON reactions(message_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_reactions_emoji ON reactions(emoji)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_mentions_message ON mentions(message_id)")
    
    conn.commit()


def process_message(msg: dict, channel_info: dict, export_date: str, conn):
    """Process a single message and insert into all relevant tables."""
    cur = conn.cursor()
    
    msg_id = msg.get('id')
    author = msg.get('author', {})
    
    # Parse timestamp
    timestamp = msg.get('timestamp', '')
    try:
        ts_epoch = int(datetime.fromisoformat(timestamp.replace('Z', '+00:00')).timestamp())
    except:
        ts_epoch = 0
    
    # Get reply reference
    reply_to = None
    if msg.get('reference'):
        reply_to = msg['reference'].get('messageId')
    
    # Count reactions
    reactions = msg.get('reactions', [])
    reactions_count = sum(r.get('count', 0) for r in reactions)
    
    # Insert message
    cur.execute("""
        INSERT OR REPLACE INTO messages 
        (id, channel_id, channel_name, channel_category, author_id, author_name, 
         author_nickname, author_color, author_is_bot, content, timestamp, timestamp_epoch,
         message_type, is_pinned, reply_to, reactions_count, attachments_count, 
         embeds_count, mentions_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        msg_id,
        channel_info.get('id'),
        channel_info.get('name'),
        channel_info.get('category'),
        author.get('id'),
        author.get('name'),
        author.get('nickname'),
        author.get('color'),
        1 if author.get('isBot') else 0,
        msg.get('content'),
        timestamp,
        ts_epoch,
        msg.get('type'),
        1 if msg.get('isPinned') else 0,
        reply_to,
        reactions_count,
        len(msg.get('attachments', [])),
        len(msg.get('embeds', [])),
        len(msg.get('mentions', []))
    ))
    
    # Insert reactions
    for reaction in reactions:
        emoji = reaction.get('emoji', {})
        emoji_str = emoji.get('name', '') if isinstance(emoji, dict) else str(emoji)
        cur.execute("""
            INSERT INTO reactions (message_id, emoji, emoji_name, count)
            VALUES (?, ?, ?, ?)
        """, (msg_id, emoji_str, emoji_str, reaction.get('count', 0)))
    
    # Insert/update author roles
    for role in author.get('roles', []):
        role_id = role.get('id')
        author_id = author.get('id')
        
        # Track first seen
        key = f"{author_id}:{role_id}"
        if key not in role_first_seen or role_first_seen[key] > export_date:
            role_first_seen[key] = export_date
        
        cur.execute("""
            INSERT OR IGNORE INTO roles 
            (author_id, author_name, role_id, role_name, role_color, role_position, first_seen_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            author_id,
            author.get('name'),
            role_id,
            role.get('name'),
            role.get('color'),
            role.get('position'),
            export_date
        ))
    
    # Insert mentions
    for mention in msg.get('mentions', []):
        cur.execute("""
            INSERT INTO mentions (message_id, mentioned_id, mentioned_name, mention_type)
            VALUES (?, ?, ?, ?)
        """, (msg_id, mention.get('id'), mention.get('name'), 'user'))
    
    # Insert attachments
    for attachment in msg.get('attachments', []):
        cur.execute("""
            INSERT INTO attachments 
            (message_id, attachment_id, filename, url, file_size, content_type)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            msg_id,
            attachment.get('id'),
            attachment.get('fileName'),
            attachment.get('url'),
            attachment.get('fileSizeBytes'),
            attachment.get('contentType')
        ))
    
    # Insert embeds
    for embed in msg.get('embeds', []):
        cur.execute("""
            INSERT INTO embeds 
            (message_id, embed_type, title, description, url, provider)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            msg_id,
            embed.get('type'),
            embed.get('title'),
            embed.get('description'),
            embed.get('url'),
            embed.get('provider', {}).get('name') if embed.get('provider') else None
        ))


def process_channel_file(json_path: Path, conn, export_date: str = None):
    """Process a single channel JSON export file."""
    if export_date is None:
        export_date = json_path.parent.name if json_path.parent.name.startswith('20') else datetime.now().strftime('%Y-%m-%d')
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    channel = data.get('channel', {})
    channel_info = {
        'id': channel.get('id'),
        'name': channel.get('name'),
        'type': channel.get('type'),
        'category_id': channel.get('categoryId'),
        'category': channel.get('category'),
        'topic': channel.get('topic')
    }
    
    # Insert channel metadata
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO channels 
        (id, name, type, category_id, category_name, topic, first_seen_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        channel_info['id'],
        channel_info['name'],
        channel_info['type'],
        channel_info['category_id'],
        channel_info['category'],
        channel_info['topic'],
        export_date
    ))
    
    # Process all messages
    for msg in data.get('messages', []):
        process_message(msg, channel_info, export_date, conn)
    
    return len(data.get('messages', []))


def compute_daily_stats(conn):
    """Compute and store daily statistics."""
    cur = conn.cursor()
    
    cur.execute("""
        INSERT OR REPLACE INTO daily_stats (date, message_count, author_count, channel_count, reaction_count, top_emoji, new_members)
        SELECT 
            date(m.timestamp) as date,
            COUNT(*) as message_count,
            COUNT(DISTINCT m.author_id) as author_count,
            COUNT(DISTINCT m.channel_id) as channel_count,
            SUM(m.reactions_count) as reaction_count,
            (SELECT emoji FROM reactions r 
             JOIN messages m2 ON r.message_id = m2.id 
             WHERE date(m2.timestamp) = date(m.timestamp) 
             GROUP BY emoji ORDER BY SUM(count) DESC LIMIT 1) as top_emoji,
            0 as new_members
        FROM messages m
        GROUP BY date(m.timestamp)
    """)
    conn.commit()


def main():
    parser = argparse.ArgumentParser(description='Ingest Discord JSON exports into SQLite')
    parser.add_argument('--input', '-i', help='Path to export directory (contains JSON files or date subdirs)')
    parser.add_argument('--output', '-o', help='Path to output SQLite database')
    parser.add_argument('--append', action='store_true', help='Append to existing database instead of replacing')
    args = parser.parse_args()
    
    # Get paths from args or environment
    input_path = Path(args.input) if args.input else (Path(os.environ['DISCORD_SOUL_INPUT']) if os.environ.get('DISCORD_SOUL_INPUT') else None)
    output_path = Path(args.output) if args.output else (Path(os.environ['DISCORD_SOUL_DB']) if os.environ.get('DISCORD_SOUL_DB') else None)
    
    if not input_path:
        print("Error: No input directory specified. Use --input or set DISCORD_SOUL_INPUT")
        sys.exit(1)
    if not output_path:
        print("Error: No output database specified. Use --output or set DISCORD_SOUL_DB")
        sys.exit(1)
    
    if not input_path.exists():
        print(f"Error: Input directory not found: {input_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("RICH DISCORD DATA INGESTION")
    print("=" * 60)
    
    # Remove old database if not appending
    if output_path.exists() and not args.append:
        output_path.unlink()
        print(f"Removed old database: {output_path}")
    
    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create database
    conn = sqlite3.connect(output_path)
    create_schema(conn)
    print(f"Database: {output_path}")
    
    # Find JSON files - either in subdirectories (date folders) or directly
    json_files = list(input_path.glob('*.json'))
    subdirs = sorted([d for d in input_path.iterdir() if d.is_dir()])
    
    total_messages = 0
    
    if subdirs and any(d.name.startswith('20') for d in subdirs):
        # Date-organized exports
        print(f"\nFound {len(subdirs)} export directories")
        for export_dir in subdirs:
            dir_files = list(export_dir.glob('*.json'))
            dir_messages = 0
            
            for json_file in dir_files:
                try:
                    count = process_channel_file(json_file, conn)
                    dir_messages += count
                except Exception as e:
                    print(f"  Error processing {json_file.name}: {e}")
            
            conn.commit()
            total_messages += dir_messages
            print(f"  {export_dir.name}: {len(dir_files)} channels, {dir_messages} messages")
    elif json_files:
        # Flat export directory
        print(f"\nFound {len(json_files)} JSON files")
        for json_file in json_files:
            try:
                count = process_channel_file(json_file, conn)
                total_messages += count
                print(f"  {json_file.name}: {count} messages")
            except Exception as e:
                print(f"  Error processing {json_file.name}: {e}")
        conn.commit()
    else:
        print("No JSON files found in input directory")
        sys.exit(1)
    
    # Compute daily stats
    print("\nComputing daily statistics...")
    compute_daily_stats(conn)
    
    # Print summary
    cur = conn.cursor()
    stats = {}
    for table in ['messages', 'reactions', 'roles', 'channels', 'mentions', 'attachments', 'embeds']:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        stats[table] = cur.fetchone()[0]
    
    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)
    print(f"""
Database: {output_path}

Tables populated:
  - messages:    {stats['messages']:,}
  - reactions:   {stats['reactions']:,}
  - roles:       {stats['roles']:,}
  - channels:    {stats['channels']:,}
  - mentions:    {stats['mentions']:,}
  - attachments: {stats['attachments']:,}
  - embeds:      {stats['embeds']:,}
""")
    
    conn.close()


if __name__ == "__main__":
    main()
