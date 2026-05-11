#!/usr/bin/env python3
"""
Ryot Collections Manager
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
        "User-Agent": "Ryot-Collections/1.0"
    }
    data = {"query": query}
    if variables:
        data["variables"] = variables
    
    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())

def list_collections():
    """List all user collections"""
    query = """
    query {
      userCollectionsList {
        id
        name
        description
        count
      }
    }
    """
    result = graphql_request(query)
    return result.get("data", {}).get("userCollectionsList", [])

def create_collection(name, description=None):
    """Create new collection"""
    query = """
    mutation ($input: CreateOrUpdateCollectionInput!) {
      createOrUpdateCollection(input: $input)
    }
    """
    variables = {
        "input": {
            "name": name
        }
    }
    if description:
        variables["input"]["description"] = description
    
    result = graphql_request(query, variables)
    return result

def add_to_collection(collection_id, metadata_ids):
    """Add metadata to collection"""
    query = """
    mutation ($input: AddEntitiesToCollectionInput!) {
      deployAddEntitiesToCollectionJob(input: $input)
    }
    """
    variables = {
        "input": {
            "collectionId": collection_id,
            "metadataIds": metadata_ids
        }
    }
    result = graphql_request(query, variables)
    return result

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  ryot_collections.py list")
        print("  ryot_collections.py create <name> [description]")
        print("  ryot_collections.py add <collection_id> <metadata_id>")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "list":
        collections = list_collections()
        if not collections:
            print("No collections found")
        else:
            for col in collections:
                print(f"📚 {col['name']} ({col['count']} items)")
                if col.get('description'):
                    print(f"   {col['description']}")
    
    elif action == "create":
        if len(sys.argv) < 3:
            print("Usage: ryot_collections.py create <name> [description]")
            sys.exit(1)
        name = sys.argv[2]
        description = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else None
        create_collection(name, description)
        print(f"✅ Collection created: {name}")
    
    elif action == "add":
        if len(sys.argv) < 4:
            print("Usage: ryot_collections.py add <collection_id> <metadata_id>")
            sys.exit(1)
        collection_id = sys.argv[2]
        metadata_id = sys.argv[3]
        add_to_collection(collection_id, [metadata_id])
        print(f"✅ Added to collection")
    
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)

if __name__ == "__main__":
    main()
