# MuleRouter Skill

A Claude Code skill for generating images and videos using MuleRouter/MuleRun multimodal APIs.

## Features

- Text-to-Image generation
- Text-to-Video generation
- Image-to-Video transformation
- Image-to-Image editing
- Video editing (VACE, keyframe interpolation)

## Requirements

- Python 3.10+
- `uv` package manager
- API key from MuleRouter or MuleRun

## Setup

```bash
# Option 1: Use custom base URL (takes priority)
export MULEROUTER_BASE_URL="https://api.mulerouter.ai"
export MULEROUTER_API_KEY="your-api-key"

# Option 2: Use site (if BASE_URL not set)
export MULEROUTER_SITE="mulerun"  # or "mulerouter"
export MULEROUTER_API_KEY="your-api-key"
```

## Usage

```bash
# List available models
uv run python scripts/list_models.py

# Generate video from text
uv run python models/alibaba/wan2.6-t2v/generation.py --prompt "A cat walking"

# Generate image from text
uv run python models/alibaba/wan2.6-t2i/generation.py --prompt "A mountain lake"
```

See [SKILL.md](SKILL.md) for detailed documentation.
