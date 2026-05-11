#!/usr/bin/env python3
"""
Analyze video using Google Gemini API (native video understanding).
Uploads video to Gemini Files API, then queries the model.

Usage:
    python3 analyze.py /path/to/video.mp4 "What's happening?"
    python3 analyze.py /path/to/video.mp4  # default: full description
    python3 analyze.py /path/to/video.mp4 "prompt" --model gemini-2.5-pro
"""
import sys, os, json, time, mimetypes, argparse
import urllib.request, urllib.error

GOOGLE_API_KEY = os.environ.get("GOOGLE_AI_API_KEY", "")
DEFAULT_MODEL = "gemini-2.5-flash"
BASE_URL = "https://generativelanguage.googleapis.com"

DEFAULT_PROMPT = (
    "Describe what's happening in this video in detail. "
    "Include any text, UI elements, spoken words, or important visual information."
)


def upload_file(filepath):
    """Upload video to Gemini Files API (resumable upload)."""
    filesize = os.path.getsize(filepath)
    mime_type = mimetypes.guess_type(filepath)[0] or "video/mp4"
    display_name = os.path.basename(filepath)

    # Initiate resumable upload
    headers = {
        "X-Goog-Upload-Protocol": "resumable",
        "X-Goog-Upload-Command": "start",
        "X-Goog-Upload-Header-Content-Length": str(filesize),
        "X-Goog-Upload-Header-Content-Type": mime_type,
        "Content-Type": "application/json",
    }
    metadata = json.dumps({"file": {"display_name": display_name}}).encode()

    req = urllib.request.Request(
        f"{BASE_URL}/upload/v1beta/files?key={GOOGLE_API_KEY}",
        data=metadata, headers=headers, method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        upload_url = resp.headers.get("X-Goog-Upload-URL")

    if not upload_url:
        raise Exception("Failed to get upload URL")

    # Upload bytes
    with open(filepath, "rb") as f:
        file_data = f.read()

    req2 = urllib.request.Request(
        upload_url, data=file_data,
        headers={
            "X-Goog-Upload-Offset": "0",
            "X-Goog-Upload-Command": "upload, finalize",
            "Content-Length": str(filesize),
        },
        method="PUT"
    )
    with urllib.request.urlopen(req2) as resp:
        result = json.loads(resp.read())

    file_uri = result.get("file", {}).get("uri", "")
    file_name = result.get("file", {}).get("name", "")
    state = result.get("file", {}).get("state", "")

    print(f"[video] Uploaded: {display_name} ({filesize:,} bytes)", file=sys.stderr)
    print(f"[video] State: {state}", file=sys.stderr)

    # Wait for processing if needed
    if state == "PROCESSING":
        print("[video] Processing...", file=sys.stderr)
        for i in range(120):
            time.sleep(5)
            check_req = urllib.request.Request(
                f"{BASE_URL}/v1beta/{file_name}?key={GOOGLE_API_KEY}"
            )
            with urllib.request.urlopen(check_req) as resp:
                status = json.loads(resp.read())
            state = status.get("state", "")
            if state == "ACTIVE":
                print("[video] Ready.", file=sys.stderr)
                break
            elif state == "FAILED":
                raise Exception(f"Processing failed: {json.dumps(status)}")

    return file_uri, mime_type, file_name


def analyze(file_uri, mime_type, prompt, model=DEFAULT_MODEL):
    """Send video to Gemini for analysis."""
    payload = {
        "contents": [{
            "parts": [
                {"file_data": {"mime_type": mime_type, "file_uri": file_uri}},
                {"text": prompt}
            ]
        }],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 8192}
    }

    req = urllib.request.Request(
        f"{BASE_URL}/v1beta/models/{model}:generateContent?key={GOOGLE_API_KEY}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=180) as resp:
        result = json.loads(resp.read())

    candidates = result.get("candidates", [])
    if candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        return "\n".join(p.get("text", "") for p in parts if "text" in p)

    return f"No response. Raw: {json.dumps(result)}"


def main():
    parser = argparse.ArgumentParser(description="Analyze video with Gemini")
    parser.add_argument("video", help="Path to video file")
    parser.add_argument("prompt", nargs="?", default=DEFAULT_PROMPT, help="Question about the video")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Gemini model (default: {DEFAULT_MODEL})")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if not GOOGLE_API_KEY:
        print("Error: Set GOOGLE_AI_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.video):
        print(f"Error: File not found: {args.video}", file=sys.stderr)
        sys.exit(1)

    file_uri, mime_type, file_name = upload_file(args.video)
    result = analyze(file_uri, mime_type, args.prompt, args.model)

    if args.json:
        print(json.dumps({"model": args.model, "prompt": args.prompt, "response": result}))
    else:
        print(result)


if __name__ == "__main__":
    main()
