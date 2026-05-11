#!/usr/bin/env python3
"""
Ryot Reviews & Ratings Manager
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
        "User-Agent": "Ryot-Reviews/1.0"
    }
    data = {"query": query}
    if variables:
        data["variables"] = variables
    
    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())

def add_review(metadata_id, rating, review_text=None):
    """Add review with rating (0-100)"""
    query = """
    mutation ($input: CreateOrUpdateReviewInput!) {
      createOrUpdateReview(input: $input)
    }
    """
    variables = {
        "input": {
            "metadataId": metadata_id,
            "rating": rating
        }
    }
    if review_text:
        variables["input"]["text"] = review_text
    
    result = graphql_request(query, variables)
    return result

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  ryot_reviews.py add <metadata_id> <rating> [review_text]")
        print("  rating: 0-100")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "add":
        if len(sys.argv) < 4:
            print("Usage: ryot_reviews.py add <metadata_id> <rating> [review_text]")
            sys.exit(1)
        
        metadata_id = sys.argv[2]
        rating = int(sys.argv[3])
        review_text = " ".join(sys.argv[4:]) if len(sys.argv) > 4 else None
        
        result = add_review(metadata_id, rating, review_text)
        print(f"✅ Review added (rating: {rating}/100)")
        if review_text:
            print(f"📝 \"{review_text}\"")
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)

if __name__ == "__main__":
    main()
