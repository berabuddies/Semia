#!/usr/bin/env python3
"""
Mark multiple episodes as watched on Ryot
"""

import json
import sys
import urllib.request
from pathlib import Path
from datetime import datetime

CONFIG_PATH = Path("/home/node/clawd/config/ryot.json")

def load_config():
    """Load Ryot configuration."""
    with open(CONFIG_PATH) as f:
        return json.load(f)

def graphql_request(query, variables=None):
    """Execute GraphQL request."""
    config = load_config()
    
    url = f"{config['url']}/backend/graphql"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['api_token']}",
        "User-Agent": "Ryot-API-Client/1.0"
    }
    
    data = {"query": query}
    if variables:
        data["variables"] = variables
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers=headers,
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            if "errors" in result:
                print(f"GraphQL Errors: {json.dumps(result['errors'], indent=2)}", file=sys.stderr)
            return result
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        raise

def search_media(title):
    """Search for media in all available sources."""
    query = """
    query ($input: MetadataSearchInput!) {
      metadataSearch(input: $input) {
        response {
          items
        }
      }
    }
    """
    
    # Try TMDB first
    sources = ["TMDB", "ANILIST", "MAL", "IGDB"]
    lots = ["SHOW", "ANIME"]
    
    for source in sources:
        for lot in lots:
            print(f"Searching in {source} for {lot}...", file=sys.stderr)
            variables = {
                "input": {
                    "search": {"query": title},
                    "lot": lot,
                    "source": source
                }
            }
            
            try:
                result = graphql_request(query, variables)
                items = result.get("data", {}).get("metadataSearch", {}).get("response", {}).get("items", [])
                
                if items:
                    print(f"Found {len(items)} results in {source} ({lot})", file=sys.stderr)
                    # Get details for first result
                    return items[0], source, lot
            except:
                continue
    
    return None, None, None

def mark_episode_watched(metadata_id, season, episode):
    """Mark a specific episode as watched."""
    query = """
    mutation ($input: [MetadataProgressUpdateInput!]!) {
      deployBulkMetadataProgressUpdate(input: $input)
    }
    """
    
    now = datetime.utcnow().isoformat() + "Z"
    
    variables = {
        "input": [{
            "metadataId": metadata_id,
            "change": {
                "createNewInProgress": {
                    "startedOn": now,
                    "showSeasonNumber": season,
                    "showEpisodeNumber": episode
                }
            }
        }]
    }
    
    result = graphql_request(query, variables)
    return result

def main():
    if len(sys.argv) < 5:
        print("Usage: ryot-mark-episodes.py <metadata_id> <season> <from_ep> <to_ep>")
        print("   or: ryot-mark-episodes.py search <title>")
        sys.exit(1)
    
    if sys.argv[1] == "search":
        title = " ".join(sys.argv[2:])
        metadata_id, source, lot = search_media(title)
        if metadata_id:
            print(f"\nFound: {metadata_id} (source: {source}, type: {lot})")
        else:
            print("Not found")
        sys.exit(0)
    
    metadata_id = sys.argv[1]
    season = int(sys.argv[2])
    from_ep = int(sys.argv[3])
    to_ep = int(sys.argv[4])
    
    print(f"Marking episodes {from_ep}-{to_ep} of season {season} as watched...")
    
    for episode in range(from_ep, to_ep + 1):
        print(f"  Episode {episode}...", end=" ")
        try:
            result = mark_episode_watched(metadata_id, season, episode)
            if "data" in result:
                print("✅")
            else:
                print(f"❌ {result.get('errors', 'Unknown error')}")
        except Exception as e:
            print(f"❌ {e}")
    
    print(f"\n✅ Done! Marked {to_ep - from_ep + 1} episodes")

if __name__ == "__main__":
    main()
