---
name: gemini-video-analyzer
description: |
  Native video analysis using Google Gemini API. Upload and analyze video files — describe scenes, extract text/UI, answer questions about content, transcribe speech, identify objects and actions. Use when: (1) User sends a video file and wants it analyzed, (2) Video summarization or description needed, (3) Extracting text, UI elements, or information from screen recordings, (4) Answering questions about video content, (5) Comparing multiple videos, (6) Analyzing tutorials, demos, or walkthroughs.
homepage: https://www.agxntsix.ai
metadata:
  {
    "openclaw":
      {
        "emoji": "🎬",
        "requires": { "bins": ["python3", "curl"], "env": ["GOOGLE_AI_API_KEY"] },
        "primaryEnv": "GOOGLE_AI_API_KEY",
      },
  }
---

# Gemini Video Analyzer

Analyze videos natively using Google Gemini's multimodal API. No frame extraction needed — Gemini processes video at 1 FPS with full motion, audio, and visual understanding.

## Quick Start

```bash
# Analyze a video with default prompt (full description)
GOOGLE_AI_API_KEY=$GOOGLE_AI_API_KEY python3 {baseDir}/scripts/analyze.py /path/to/video.mp4

# Ask a specific question
GOOGLE_AI_API_KEY=$GOOGLE_AI_API_KEY python3 {baseDir}/scripts/analyze.py /path/to/video.mp4 "What text is visible on screen?"

# Manage uploaded files
GOOGLE_AI_API_KEY=$GOOGLE_AI_API_KEY python3 {baseDir}/scripts/manage_files.py list
GOOGLE_AI_API_KEY=$GOOGLE_AI_API_KEY python3 {baseDir}/scripts/manage_files.py cleanup
```

## Supported Formats

MP4, AVI, MOV, MKV, WebM, FLV, MPEG, MPG, WMV, 3GP — up to 2GB per file.

## How It Works

1. Video uploads to Google's Files API (temporary, auto-deletes after 48h)
2. Gemini processes at 1 frame/sec — understands motion, transitions, audio context
3. Model generates response based on your prompt
4. Way better than frame extraction for understanding temporal content

## Use Cases

| Task | Example Prompt |
|------|---------------|
| General description | *(default — no prompt needed)* |
| UI/text extraction | `"What text and UI elements are visible?"` |
| Tutorial summary | `"Summarize the steps shown in this tutorial"` |
| Bug report from video | `"Describe what went wrong in this screen recording"` |
| Meeting notes | `"Summarize the key points discussed"` |
| Content comparison | Upload 2 videos, ask for differences |

## Configuration

Set `GOOGLE_AI_API_KEY` in your environment or `.env` file. Get a free key at [aistudio.google.com](https://aistudio.google.com/apikey).

Default model: `gemini-2.5-flash` (fast, cheap, excellent vision). Override with `--model gemini-2.5-pro` for complex analysis.

## API Reference

See [references/gemini-files-api.md](references/gemini-files-api.md) for file upload limits, processing details, and advanced options.
