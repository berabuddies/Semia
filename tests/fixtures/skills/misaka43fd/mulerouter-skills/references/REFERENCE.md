# MuleRouter API Reference

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `MULEROUTER_API_KEY` | Yes | API key for authentication |
| `MULEROUTER_BASE_URL` | No* | Custom API base URL (takes priority over SITE) |
| `MULEROUTER_SITE` | No* | API site: `mulerouter` or `mulerun` |

*Either `MULEROUTER_BASE_URL` or `MULEROUTER_SITE` must be set.

### .env File Example

```env
# Option 1: Use custom base URL (takes priority)
MULEROUTER_BASE_URL=https://api.mulerouter.ai
MULEROUTER_API_KEY=your-api-key

# Option 2: Use site (if BASE_URL not set)
# MULEROUTER_SITE=mulerun
# MULEROUTER_API_KEY=your-api-key
```

## CLI Options

All model scripts support these options:

| Option | Description |
|--------|-------------|
| `--list-params` | Show available parameters and exit |
| `--json` | Output results as JSON |
| `--no-wait` | Return task ID immediately without polling |
| `--poll-interval N` | Polling interval in seconds (default: 5) |
| `--max-wait N` | Maximum wait time in seconds (default: 600) |
| `--quiet` | Suppress progress output |
| `--base-url URL` | Override API base URL (takes priority over --site) |
| `--site SITE` | Override API site (mulerouter/mulerun) |
| `--api-key KEY` | Override API key |

## Task Workflow

All generation tasks are asynchronous:

1. **Create Task**: POST request returns a task ID
2. **Poll Status**: GET request checks task status (pending -> processing -> completed/failed)
3. **Get Results**: Completed tasks include URLs to generated images/videos

The scripts handle polling automatically. Use `--no-wait` for manual control.

## API Sites

| Site | Base URL | Notes |
|------|----------|-------|
| MuleRouter | `api.mulerouter.ai` | Full model catalog |
| MuleRun | `api.mulerun.com` | Full model catalog |

Both sites share the same API format. Model availability may differ between sites.

## Error Handling

Common error responses:

| Code | Meaning | Solution |
|------|---------|----------|
| 401 | Invalid API key | Check MULEROUTER_API_KEY |
| 400 | Invalid parameters | Run `--list-params` to see valid options |
| 429 | Rate limited | Wait and retry |
| 500 | Server error | Retry after a few seconds |

## Output Format

### JSON Output (--json)

```json
{
  "task_id": "2227246C-760C-4167-906C-DD727D7BBBEC",
  "status": "completed",
  "videos": ["https://..."],
  "images": ["https://..."]
}
```

### Default Output

```
Task ID: 2227246C-760C-4167-906C-DD727D7BBBEC
Status: completed
Result URLs:
  - https://...
```
