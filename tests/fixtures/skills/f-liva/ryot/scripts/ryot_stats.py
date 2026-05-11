#!/usr/bin/env python3
"""
Ryot Analytics & Statistics
"""

import json
import sys
import urllib.request
from pathlib import Path

CONFIG_PATH = Path("/home/node/clawd/config/ryot.json")

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def graphql_request(query, variables=None):
    config = load_config()
    url = f"{config['url']}/backend/graphql"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['api_token']}",
        "User-Agent": "Ryot-Stats/1.0"
    }
    data = {"query": query}
    if variables:
        data["variables"] = variables
    
    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())

def get_analytics():
    """Get user analytics"""
    # First get parameters
    params_query = """
    query {
      userAnalyticsParameters {
        mediaLots
        genres
      }
    }
    """
    params = graphql_request(params_query)
    media_lots = params.get("data", {}).get("userAnalyticsParameters", {}).get("mediaLots", ["SHOW"])
    
    # Then get analytics for first media type
    lot = media_lots[0] if media_lots else "SHOW"
    analytics_query = """
    query ($input: UserAnalyticsInput!) {
      userAnalytics(input: $input) {
        mediaOverall {
          metadataCount
          uniqueShowsCount
          uniqueMoviesCount
          totalWatchTime
        }
      }
    }
    """
    variables = {"input": {"lot": lot}}
    result = graphql_request(analytics_query, variables)
    return result.get("data", {}).get("userAnalytics", {})

def get_recent():
    """Get recently consumed media (last 20)"""
    query = """
    query {
      userMetadataList(input: { lot: SHOW }) {
        response {
          metadataId
          title
          lastSeen
        }
      }
    }
    """
    try:
        result = graphql_request(query)
        if not result or "data" not in result:
            return []
        items = result.get("data", {}).get("userMetadataList", {}).get("response", [])
        # Sort by lastSeen
        sorted_items = sorted([i for i in items if i.get('lastSeen')], key=lambda x: x['lastSeen'], reverse=True)
        return sorted_items[:20]
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return []

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  ryot_stats.py analytics")
        print("  ryot_stats.py recent")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "analytics":
        analytics = get_analytics()
        overall = analytics.get("mediaOverall", {})
        
        print("📊 RYOT ANALYTICS")
        print(f"\n📺 Media tracked: {overall.get('metadataCount', 0)}")
        if overall.get('uniqueShowsCount'):
            print(f"   TV Shows: {overall['uniqueShowsCount']}")
        if overall.get('uniqueMoviesCount'):
            print(f"   Movies: {overall['uniqueMoviesCount']}")
        if overall.get('totalWatchTime'):
            hours = overall['totalWatchTime'] / 60
            print(f"   Total watch time: {hours:.1f} hours")
    
    elif action == "recent":
        items = get_recent()
        if not items:
            print("No recent media")
        else:
            print("🕒 RECENTLY WATCHED/READ")
            for item in items[:10]:
                print(f"📺 {item['title']}")
                if item.get('lastSeen'):
                    print(f"   Last seen: {item['lastSeen'][:10]}")
    
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)

if __name__ == "__main__":
    main()
