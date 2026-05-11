# LanceDB Integration

Semantic search over Discord exports using vector embeddings.

## Prerequisites

```bash
pip install lancedb sentence-transformers
```

## Quick Setup

### 1. Index Discord Exports

```python
#!/usr/bin/env python3
# save as: scripts/index-to-lancedb.py

import json
import lancedb
from pathlib import Path
from sentence_transformers import SentenceTransformer
import sys

def index_discord(json_dir: str, db_path: str):
    """Index Discord JSON exports into LanceDB"""
    model = SentenceTransformer('all-MiniLM-L6-v2')
    db = lancedb.connect(db_path)
    
    records = []
    json_dir = Path(json_dir)
    
    for json_file in json_dir.glob('*.json'):
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        channel = data.get('channel', {}).get('name', json_file.stem)
        
        for msg in data.get('messages', []):
            content = msg.get('content', '').strip()
            if not content or len(content) < 10:
                continue
            
            records.append({
                'id': msg.get('id'),
                'channel': channel,
                'author': msg.get('author', {}).get('name', 'Unknown'),
                'content': content,
                'timestamp': msg.get('timestamp'),
                'vector': model.encode(content).tolist()
            })
    
    if records:
        # Create or overwrite table
        table = db.create_table('discord_messages', records, mode='overwrite')
        print(f"Indexed {len(records)} messages → {db_path}")
    else:
        print("No messages to index")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python index-to-lancedb.py <json_dir> <lancedb_path>")
        sys.exit(1)
    index_discord(sys.argv[1], sys.argv[2])
```

### 2. Search

```python
#!/usr/bin/env python3
# save as: scripts/search-lancedb.py

import lancedb
from sentence_transformers import SentenceTransformer
import sys

def search(db_path: str, query: str, limit: int = 10):
    """Semantic search over indexed Discord messages"""
    model = SentenceTransformer('all-MiniLM-L6-v2')
    db = lancedb.connect(db_path)
    
    table = db.open_table('discord_messages')
    query_vector = model.encode(query).tolist()
    
    results = table.search(query_vector).limit(limit).to_pandas()
    
    for _, row in results.iterrows():
        print(f"[{row['channel']}] @{row['author']}: {row['content'][:100]}...")
        print(f"  Score: {row['_distance']:.4f}")
        print()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python search-lancedb.py <lancedb_path> <query>")
        sys.exit(1)
    search(sys.argv[1], ' '.join(sys.argv[2:]))
```

## Integration with Export Pipeline

Add to your export cron:

```bash
# After JSON export and SQLite conversion
python scripts/index-to-lancedb.py \
    ./discord-export/$(date +%Y-%m-%d) \
    ./discord-vectors/
```

## Incremental Updates

For large archives, use incremental indexing:

```python
def index_incremental(json_dir: str, db_path: str, since_timestamp: str):
    """Only index messages newer than timestamp"""
    # ... filter messages by timestamp before indexing
    pass
```

## Advanced Queries

### Hybrid Search (semantic + keyword)

```python
results = (table
    .search(query_vector)
    .where(f"channel = '{channel_name}'")
    .limit(10)
    .to_pandas())
```

### Author Filter

```python
results = (table
    .search(query_vector)
    .where("author = 'username'")
    .limit(20)
    .to_pandas())
```

### Time Range

```python
results = (table
    .search(query_vector)
    .where("timestamp > '2025-01-01'")
    .limit(10)
    .to_pandas())
```

## Storage Estimates

- ~1KB per message (with 384-dim vector)
- 10K messages ≈ 10MB
- 100K messages ≈ 100MB

## Model Options

| Model | Dimensions | Speed | Quality |
|-------|------------|-------|---------|
| all-MiniLM-L6-v2 | 384 | Fast | Good |
| all-mpnet-base-v2 | 768 | Medium | Better |
| text-embedding-3-small | 1536 | API | Best |

For most Discord use cases, MiniLM is sufficient and runs locally.
