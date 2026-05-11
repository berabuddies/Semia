#!/usr/bin/env python3
"""
Ryot Media Tracker API Client
Supports search, details, and marking media as completed.
"""

import json
import sys
import urllib.request
import urllib.parse
from pathlib import Path

# Load config
CONFIG_PATH = Path("/home/node/clawd/config/ryot.json")

def load_config():
    """Load Ryot configuration from JSON file."""
    with open(CONFIG_PATH) as f:
        return json.load(f)

def graphql_request(query, variables=None):
    """Execute a GraphQL request to Ryot API."""
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
    
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())

def search_media(title, media_type="SHOW", source="TMDB"):
    """Search for media by title. Returns list of metadata IDs."""
    query = """
    query ($input: MetadataSearchInput!) {
      metadataSearch(input: $input) {
        response {
          items
        }
      }
    }
    """
    
    variables = {
        "input": {
            "search": {"query": title},
            "lot": media_type,
            "source": source
        }
    }
    
    result = graphql_request(query, variables)
    items = result.get("data", {}).get("metadataSearch", {}).get("response", {}).get("items", [])
    
    # items is an array of strings (metadata IDs)
    # Get details for each to show title/year
    detailed_items = []
    for item_id in items[:5]:  # Limit to first 5 results
        details = get_details(item_id)
        detailed_items.append({
            "id": item_id,
            "title": details.get("title", ""),
            "year": details.get("publishYear", "")
        })
    
    return detailed_items

def get_details(metadata_id):
    """Get detailed information about a media item."""
    query = """
    query ($metadataId: String!) {
      metadataDetails(metadataId: $metadataId) {
        response {
          title
          publishYear
          description
        }
      }
    }
    """
    
    variables = {"metadataId": metadata_id}
    result = graphql_request(query, variables)
    
    return result.get("data", {}).get("metadataDetails", {}).get("response", {})

def get_progress(metadata_id):
    """Get user's viewing/reading progress for a show."""
    # First get basic details
    details_query = """
    query ($metadataId: String!) {
      metadataDetails(metadataId: $metadataId) {
        response {
          title
          showSpecifics {
            totalSeasons
            totalEpisodes
          }
        }
      }
    }
    """
    
    details_result = graphql_request(details_query, {"metadataId": metadata_id})
    details_data = details_result.get("data", {}).get("metadataDetails", {}).get("response", {})
    
    # Get user progress
    progress_query = """
    query ($metadataId: String!) {
      userMetadataDetails(metadataId: $metadataId) {
        response {
          inProgress {
            showExtraInformation {
              season
              episode
            }
          }
        }
      }
    }
    """
    
    progress_result = graphql_request(progress_query, {"metadataId": metadata_id})
    user_data = progress_result.get("data", {}).get("userMetadataDetails", {}).get("response", {})
    
    return {
        "title": details_data.get("title", ""),
        "totalEpisodes": details_data.get("showSpecifics", {}).get("totalEpisodes", 0),
        "totalSeasons": details_data.get("showSpecifics", {}).get("totalSeasons", 0),
        "currentSeason": user_data.get("inProgress", {}).get("showExtraInformation", {}).get("season"),
        "currentEpisode": user_data.get("inProgress", {}).get("showExtraInformation", {}).get("episode")
    }

def mark_completed(metadata_id):
    """Mark media as completed."""
    query = """
    mutation ($input: [BulkMediaProgressInput!]!) {
      deployBulkMetadataProgressUpdate(input: $input)
    }
    """
    
    variables = {
        "input": [{
            "metadataId": metadata_id,
            "change": {"createNewCompleted": {"withoutDates": {}}}
        }]
    }
    
    result = graphql_request(query, variables)
    return result

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  ryot_api.py search <title> [--type SHOW|MOVIE|BOOK|ANIME|GAME]")
        print("  ryot_api.py details <metadata_id>")
        print("  ryot_api.py progress <metadata_id>")
        print("  ryot_api.py complete <metadata_id>")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "search":
        if len(sys.argv) < 3:
            print("Usage: ryot_api.py search <title> [--type TYPE]")
            sys.exit(1)
        
        title = sys.argv[2]
        media_type = "SHOW"  # default
        
        # Parse optional --type flag
        if len(sys.argv) > 3 and sys.argv[3] == "--type":
            if len(sys.argv) > 4:
                media_type = sys.argv[4]
        
        results = search_media(title, media_type)
        print(json.dumps(results, indent=2))
    
    elif action == "details":
        if len(sys.argv) < 3:
            print("Usage: ryot_api.py details <metadata_id>")
            sys.exit(1)
        
        metadata_id = sys.argv[2]
        details = get_details(metadata_id)
        print(json.dumps(details, indent=2))
    
    elif action == "progress":
        if len(sys.argv) < 3:
            print("Usage: ryot_api.py progress <metadata_id>")
            sys.exit(1)
        
        metadata_id = sys.argv[2]
        progress = get_progress(metadata_id)
        
        if progress.get("currentEpisode"):
            current_ep = progress["currentEpisode"]
            total_ep = progress["totalEpisodes"]
            percentage = int((current_ep / total_ep * 100)) if total_ep > 0 else 0
            
            print(f"{progress['title']}")
            print(f"Season {progress['currentSeason']}, Episode {current_ep}/{total_ep} ({percentage}%)")
        else:
            print(f"{progress['title']}")
            print("Not started yet")
    
    elif action == "complete":
        if len(sys.argv) < 3:
            print("Usage: ryot_api.py complete <metadata_id>")
            sys.exit(1)
        
        metadata_id = sys.argv[2]
        result = mark_completed(metadata_id)
        print(json.dumps(result, indent=2))
        print(f"\n✅ Marked {metadata_id} as completed")
    
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)

if __name__ == "__main__":
    main()
