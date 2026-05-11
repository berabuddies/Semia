# Model Reference

## Discovering Models

Run `python scripts/list_models.py` to see available models:

```bash
# List all models
python scripts/list_models.py

# Filter by provider
python scripts/list_models.py --provider alibaba

# Filter by output type
python scripts/list_models.py --output-type video

# JSON output
python scripts/list_models.py --json
```

## Model Categories

### Text-to-Image (T2I)

| Model | Path | Description |
|-------|------|-------------|
| Wan2.6 T2I | `models/alibaba/wan2.6-t2i/generation.py` | Flagship image generation |
| Wan2.5 T2I Preview | `models/alibaba/wan2.5-t2i-preview/generation.py` | Preview model |
| Nano Banana Pro | `models/google/nano-banana-pro/generation.py` | High-resolution images |
| Midjourney Diffusion | `models/midjourney/diffusion/generation.py` | Midjourney image generation |

### Text-to-Video (T2V)

| Model | Path | Description |
|-------|------|-------------|
| Wan2.6 T2V | `models/alibaba/wan2.6-t2v/generation.py` | Flagship video generation |
| Wan2.5 T2V Preview | `models/alibaba/wan2.5-t2v-preview/generation.py` | Preview model |
| Wan2.2 T2V Plus | `models/alibaba/wan2.2-t2v-plus/generation.py` | Previous generation |
| Veo 3 | `models/google/veo3/generation.py` | Google Veo 3 video generation (mulerun only) |
| Sora 2 | `models/openai/sora2/generation.py` | OpenAI Sora 2 video generation (mulerun only) |

### Image-to-Video (I2V)

| Model | Path | Description |
|-------|------|-------------|
| Wan2.6 I2V | `models/alibaba/wan2.6-i2v/generation.py` | Flagship image animation |
| Wan2.5 I2V Preview | `models/alibaba/wan2.5-i2v-preview/generation.py` | Preview model |
| Wan2.2 I2V Plus | `models/alibaba/wan2.2-i2v-plus/generation.py` | High quality |
| Wan2.2 I2V Flash | `models/alibaba/wan2.2-i2v-flash/generation.py` | 50% faster |
| Veo 3 | `models/google/veo3/generation.py` | Google Veo 3 with image input (mulerun only) |
| Sora 2 | `models/openai/sora2/generation.py` | OpenAI Sora 2 with image input (mulerun only) |
| Midjourney Video | `models/midjourney/video/generation.py` | Image-to-video (prompt must include image URL) |

### Image-to-Image (I2I)

| Model | Path | Description |
|-------|------|-------------|
| Wan2.5 I2I Preview | `models/alibaba/wan2.5-i2i-preview/generation.py` | Image editing |
| Nano Banana Pro Edit | `models/google/nano-banana-pro/edit.py` | Image editing |

### Advanced Video Editing

| Model | Path | Description |
|-------|------|-------------|
| Wan2.6 Image | `models/alibaba/wan2.6-image/generation.py` | Image processing |
| Wan2.1 VACE Plus | `models/alibaba/wan2.1-vace-plus/generation.py` | Video outpainting |
| Wan2.1 KF2V Plus | `models/alibaba/wan2.1-kf2v-plus/generation.py` | Keyframe interpolation |

## Checking Parameters

Before calling a model, use `--list-params`:

```bash
python models/alibaba/wan2.6-t2v/generation.py --list-params
```

Example output:

```
Parameters for alibaba/wan2.6-t2v generation:

Required:
  --prompt TEXT          Text description for video content (max 2000 chars)

Optional:
  --negative-prompt TEXT Unwanted content description
  --size TEXT            Resolution: 1280*720 (default), 1920*1080, etc.
  --duration INT         Duration: 5 (default), 10, or 15 seconds
  --seed INT             Random seed for reproducibility
```

## Common Parameters

| Parameter | Type | Models | Description |
|-----------|------|--------|-------------|
| `--prompt` | string | All | Content description (required) |
| `--negative-prompt` | string | Most | Unwanted content |
| `--size` | string | Video | Resolution (width*height) |
| `--resolution` | string | Some | 720P, 1080P, 2K |
| `--duration` | int | Video | Length in seconds |
| `--seed` | int | All | Reproducibility seed |
| `--image` | string | I2V/I2I | Input image URL |
