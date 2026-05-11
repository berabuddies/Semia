#!/usr/bin/env python3
"""
Manage files in Google Gemini Files API.
List, inspect, and clean up uploaded video files.

Usage:
    python3 manage_files.py list          # List all uploaded files
    python3 manage_files.py cleanup       # Delete all uploaded files
    python3 manage_files.py delete <name> # Delete a specific file
"""
import sys, os, json
import urllib.request

GOOGLE_API_KEY = os.environ.get("GOOGLE_AI_API_KEY", "")
BASE_URL = "https://generativelanguage.googleapis.com"


def list_files():
    req = urllib.request.Request(f"{BASE_URL}/v1beta/files?key={GOOGLE_API_KEY}")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    files = data.get("files", [])
    if not files:
        print("No files uploaded.")
        return
    for f in files:
        size = int(f.get("sizeBytes", 0))
        print(f"  {f.get('name', '?'):40s}  {f.get('displayName', '?'):30s}  {size:>12,} bytes  {f.get('state', '?')}")
    print(f"\nTotal: {len(files)} files")


def delete_file(name):
    req = urllib.request.Request(
        f"{BASE_URL}/v1beta/{name}?key={GOOGLE_API_KEY}",
        method="DELETE"
    )
    urllib.request.urlopen(req)
    print(f"Deleted: {name}")


def cleanup():
    req = urllib.request.Request(f"{BASE_URL}/v1beta/files?key={GOOGLE_API_KEY}")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    files = data.get("files", [])
    if not files:
        print("No files to clean up.")
        return
    for f in files:
        try:
            delete_file(f["name"])
        except Exception as e:
            print(f"Failed to delete {f['name']}: {e}")
    print(f"\nCleaned up {len(files)} files.")


if __name__ == "__main__":
    if not GOOGLE_API_KEY:
        print("Error: Set GOOGLE_AI_API_KEY", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "list":
        list_files()
    elif cmd == "cleanup":
        cleanup()
    elif cmd == "delete" and len(sys.argv) > 2:
        delete_file(sys.argv[2])
    else:
        print("Usage: manage_files.py [list|cleanup|delete <name>]")
