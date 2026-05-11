#!/usr/bin/env python3
"""
Ryot Calendar & Upcoming Episodes
"""

import json
import sys
import urllib.request
from datetime import datetime, timedelta
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
        "User-Agent": "Ryot-Calendar/1.0"
    }
    data = {"query": query}
    if variables:
        data["variables"] = variables
    
    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())

def get_upcoming():
    """Get upcoming calendar events (next 7 days)"""
    query = """
    query {
      userUpcomingCalendarEvents(input: {}) {
        date
        events {
          metadataTitle
          metadataLot
          showExtraInformation {
            season
            episode
          }
        }
      }
    }
    """
    result = graphql_request(query)
    return result.get("data", {}).get("userUpcomingCalendarEvents", [])

def get_calendar(days=30):
    """Get calendar events for next N days"""
    query = """
    query ($input: UserCalendarEventInput!) {
      userCalendarEvents(input: $input) {
        date
        events {
          metadataTitle
          metadataLot
          showExtraInformation {
            season
            episode
          }
        }
      }
    }
    """
    end_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    variables = {"input": {"endDate": end_date}}
    result = graphql_request(query, variables)
    return result.get("data", {}).get("userCalendarEvents", [])

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  ryot_calendar.py upcoming")
        print("  ryot_calendar.py calendar [days]")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "upcoming":
        events = get_upcoming()
        if not events:
            print("No upcoming episodes")
        else:
            print("📅 UPCOMING THIS WEEK")
            for day in events:
                print(f"\n{day['date']}")
                for event in day['events']:
                    if event.get('showExtraInformation'):
                        season = event['showExtraInformation'].get('season', '?')
                        episode = event['showExtraInformation'].get('episode', '?')
                        print(f"  📺 {event['metadataTitle']} - S{season}E{episode}")
                    else:
                        print(f"  📺 {event['metadataTitle']}")
    
    elif action == "calendar":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        events = get_calendar(days)
        if not events:
            print(f"No events in next {days} days")
        else:
            print(f"📅 CALENDAR (next {days} days)")
            for day in events[:10]:  # Limit to 10 days
                print(f"\n{day['date']}")
                for event in day['events']:
                    if event.get('showExtraInformation'):
                        season = event['showExtraInformation'].get('season', '?')
                        episode = event['showExtraInformation'].get('episode', '?')
                        print(f"  📺 {event['metadataTitle']} - S{season}E{episode}")
                    else:
                        print(f"  📺 {event['metadataTitle']}")
    
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)

if __name__ == "__main__":
    main()
