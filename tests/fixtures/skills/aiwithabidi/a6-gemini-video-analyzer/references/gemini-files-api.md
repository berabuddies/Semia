# Gemini Files API Reference

## Upload Limits
- Max file size: 2GB per video
- Project quota: 20GB total storage
- Storage duration: 48 hours (auto-deleted)
- Processing rate: 1 frame per second

## Supported Video Formats
MP4, AVI, MOV, MKV, WebM, FLV, MPEG, MPG, WMV, 3GP

## Processing
- Videos are processed server-side at 1 FPS
- Small videos (<100MB) can be sent inline
- Larger videos use resumable upload via Files API
- Same file URI can be reused across multiple prompts (within 48h)

## Models
| Model | Context | Cost (in/out per 1M) | Best For |
|-------|---------|---------------------|----------|
| gemini-2.5-flash | 1M tokens | $0.30/$2.50 | Fast, cheap, daily use |
| gemini-2.5-pro | 1M tokens | $1.25/$10.00 | Complex analysis |
| gemini-3-flash-preview | 1M tokens | $0.50/$3.00 | Latest vision |

## Token Usage
- Video: ~258 tokens per second of content
- 1 minute video ≈ 15,480 tokens
- 1 hour video ≈ 928,800 tokens (fits in 1M context)

## Tips
- Reuse file URIs to avoid re-uploading the same video
- Use `manage_files.py cleanup` to free quota when done
- For batch analysis, upload all videos first, then query
