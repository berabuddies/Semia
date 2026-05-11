---
name: mulerouter
description: Generates images and videos using MuleRouter or MuleRun multimodal APIs. Text-to-Image, Image-to-Image, Text-to-Video, Image-to-Video, video editing (VACE, keyframe interpolation). Use when the user wants to generate, edit, or transform images and videos using AI models like Wan2.6, Veo3, Nano Banana Pro, Sora2, Midjourney.
compatibility: Requires Python 3.10+, uv (or pip), and network access to api.mulerouter.ai or api.mulerun.com
---

# MuleRouter API

Generate images and videos using MuleRouter or MuleRun multimodal APIs.

## Configuration Check

Before running any commands, verify the environment is configured:

### Step 1: Check for existing configuration

```bash
# Check environment variables
echo "MULEROUTER_BASE_URL: $MULEROUTER_BASE_URL"
echo "MULEROUTER_SITE: $MULEROUTER_SITE"
echo "MULEROUTER_API_KEY: ${MULEROUTER_API_KEY:+[SET]}"

# Check for .env file
ls -la .env 2>/dev/null || echo "No .env file found"
```

### Step 2: Configure if needed

**Option A: Environment variables with custom base URL (highest priority)**
```bash
export MULEROUTER_BASE_URL="https://api.mulerouter.ai"  # or your custom API endpoint
export MULEROUTER_API_KEY="your-api-key"
```

**Option B: Environment variables with site (used if base URL not set)**
```bash
export MULEROUTER_SITE="mulerun"    # or "mulerouter"
export MULEROUTER_API_KEY="your-api-key"
```

**Option C: Create .env file**

Create `.env` in the current working directory:

```env
# Option 1: Use custom base URL (takes priority over SITE)
MULEROUTER_BASE_URL=https://api.mulerouter.ai
MULEROUTER_API_KEY=your-api-key

# Option 2: Use site (if BASE_URL not set)
# MULEROUTER_SITE=mulerun
# MULEROUTER_API_KEY=your-api-key
```

**Note:** `MULEROUTER_BASE_URL` takes priority over `MULEROUTER_SITE`. If both are set, `MULEROUTER_BASE_URL` is used.

**Note:** The tool only reads `.env` from the current directory. Run scripts from the skill root (`skills/mulerouter-skills/`).

### Step 3: Using `uv` to run scripts

The skill uses `uv` for dependency management and execution. Make sure `uv` is installed and available in your PATH.

Run `uv sync` to install dependencies.

## Quick Start

### 1. List available models

```bash
uv run python scripts/list_models.py
```

### 2. Check model parameters

```bash
uv run python models/alibaba/wan2.6-t2v/generation.py --list-params
```

### 3. Generate content

**Text-to-Video:**
```bash
uv run python models/alibaba/wan2.6-t2v/generation.py --prompt "A cat walking through a garden"
```

**Text-to-Image:**
```bash
uv run python models/alibaba/wan2.6-t2i/generation.py --prompt "A serene mountain lake"
```

**Image-to-Video:**
```bash
uv run python models/alibaba/wan2.6-i2v/generation.py --prompt "Gentle zoom in" --image "https://example.com/photo.jpg" #remote image url
```
```bash
uv run python models/alibaba/wan2.6-i2v/generation.py --prompt "Gentle zoom in" --image "/path/to/local/image.png" #local image path
```

## Image Input

For image parameters (`--image`, `--images`, etc.), **prefer local file paths** over base64.

```bash
# Preferred: local file path (auto-converted to base64)
--image /tmp/photo.png

--images ["/tmp/photo.png"]
```

The skill automatically converts local file paths to base64 before sending to the API. This avoids command-line length limits that occur with raw base64 strings.

## Workflow

1. Check configuration: verify `MULEROUTER_BASE_URL` or `MULEROUTER_SITE`, and `MULEROUTER_API_KEY` are set
2. Install dependencies: run `uv sync`
3. Run `uv run python scripts/list_models.py` to discover available models
4. Run `uv run python models/<path>/<action>.py --list-params` to see parameters
5. Execute with appropriate parameters
6. Parse output URLs from results

## Tips
1. For an image generation model, a suggested timeout is 5 minutes.
2. For a video generation model, a suggested timeout is 15 minutes.

## References

- [REFERENCE.md](references/REFERENCE.md) - API configuration and CLI options
- [MODELS.md](references/MODELS.md) - Complete model specifications
