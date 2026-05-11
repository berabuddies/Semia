#!/usr/bin/env python3
"""
Regex content filter for Discord messages.
Flags messages with potential prompt injection patterns.
Run after export, before Haiku screening (or as additional layer).
"""

import sqlite3
import re
import sys
from pathlib import Path

DB_PATH = Path("./discord.db")

# Prompt injection patterns (case-insensitive)
SUSPICIOUS_PATTERNS = [
    # Direct instruction override
    r"ignore\s+(all\s+)?previous\s+instructions?",
    r"disregard\s+(all\s+)?(your\s+)?instructions?",
    r"forget\s+(all\s+)?previous",
    r"override\s+(your\s+)?instructions?",
    r"new\s+instructions?:",
    
    # Role/persona hijacking
    r"you\s+are\s+now\s+a",
    r"pretend\s+(you('re|are)\s+)?",
    r"act\s+as\s+(if\s+you('re|are)\s+)?",
    r"roleplay\s+as",
    r"from\s+now\s+on\s+you('re|are)",
    
    # System prompt injection
    r"<\s*system\s*>",
    r"<\s*/?\s*instruction",
    r"\[\s*SYSTEM\s*\]",
    r"\[\s*INST\s*\]",
    r"<<\s*SYS\s*>>",
    
    # Jailbreak attempts
    r"DAN\s+mode",
    r"developer\s+mode",
    r"jailbreak",
    r"bypass\s+(your\s+)?(safety|filter|restriction)",
    
    # Manipulation keywords
    r"IMPORTANT\s*:",
    r"CRITICAL\s*:",
    r"URGENT\s*:",
    r"ATTENTION\s*:",
    r"^STOP[.!]",
    
    # Output manipulation
    r"respond\s+with\s+only",
    r"output\s+only",
    r"say\s+exactly",
    r"repeat\s+after\s+me",
    
    # Data exfiltration
    r"(reveal|show|tell|share)\s+(me\s+)?(your|the)\s+(system\s+)?prompt",
    r"what\s+(are|is)\s+your\s+instructions?",
    r"print\s+(your\s+)?config",
]

# Compile patterns for efficiency
COMPILED_PATTERNS = [
    (re.compile(p, re.IGNORECASE | re.MULTILINE), p) 
    for p in SUSPICIOUS_PATTERNS
]

def scan_message(content: str) -> list[str]:
    """Return list of matched pattern descriptions."""
    if not content:
        return []
    
    matches = []
    for compiled, original in COMPILED_PATTERNS:
        if compiled.search(content):
            matches.append(original)
    return matches

def scan_database(db_path: Path, update: bool = False) -> dict:
    """Scan all messages and optionally update safety_status."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all messages (or just pending ones)
    cursor.execute("""
        SELECT id, content, author_name, channel_name, safety_status
        FROM messages
        WHERE content IS NOT NULL AND content != ''
    """)
    
    results = {
        "scanned": 0,
        "flagged": 0,
        "patterns": {},
        "flagged_messages": []
    }
    
    flagged_ids = []
    
    for row in cursor.fetchall():
        results["scanned"] += 1
        matches = scan_message(row["content"])
        
        if matches:
            results["flagged"] += 1
            flagged_ids.append(row["id"])
            
            # Track pattern frequency
            for pattern in matches:
                results["patterns"][pattern] = results["patterns"].get(pattern, 0) + 1
            
            results["flagged_messages"].append({
                "id": row["id"],
                "author": row["author_name"],
                "channel": row["channel_name"],
                "content": row["content"][:200] + "..." if len(row["content"]) > 200 else row["content"],
                "patterns": matches,
                "current_status": row["safety_status"]
            })
    
    # Update safety_status if requested
    if update and flagged_ids:
        cursor.executemany(
            "UPDATE messages SET safety_status = 'regex_flagged', safety_flags = 'regex_match' WHERE id = ?",
            [(id,) for id in flagged_ids]
        )
        conn.commit()
        results["updated"] = len(flagged_ids)
    
    conn.close()
    return results

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Scan Discord messages for prompt injection patterns")
    parser.add_argument("--update", action="store_true", help="Update safety_status for flagged messages")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="Path to SQLite database")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()
    
    if not args.db.exists():
        print(f"Database not found: {args.db}", file=sys.stderr)
        sys.exit(1)
    
    results = scan_database(args.db, update=args.update)
    
    if args.json:
        import json
        print(json.dumps(results, indent=2))
    else:
        print(f"📊 Scanned: {results['scanned']} messages")
        print(f"🚩 Flagged: {results['flagged']} messages")
        
        if results["flagged"] > 0:
            print(f"\n📋 Pattern matches:")
            for pattern, count in sorted(results["patterns"].items(), key=lambda x: -x[1]):
                print(f"  {count}x: {pattern[:60]}...")
            
            print(f"\n⚠️  Flagged messages:")
            for msg in results["flagged_messages"][:10]:  # Show first 10
                print(f"  [{msg['channel']}] {msg['author']}: {msg['content'][:80]}...")
                print(f"    Patterns: {', '.join(msg['patterns'][:3])}")
            
            if len(results["flagged_messages"]) > 10:
                print(f"  ... and {len(results['flagged_messages']) - 10} more")
        
        if args.update:
            print(f"\n✅ Updated {results.get('updated', 0)} messages to 'regex_flagged'")

if __name__ == "__main__":
    main()
