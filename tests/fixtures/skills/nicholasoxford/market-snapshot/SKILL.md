---
name: market-snapshot
description: Fetch a token market snapshot (price/liquidity/volume) and return stable JSON (backed by Jupiter).
homepage: https://app.vecstack.com
---

# Market Snapshot (Skill-Only, OpenClaw)

This skill is designed for OpenClaw/ClawHub bots that need a fast, low-friction market snapshot.

## What This Skill Does

- Calls a hosted market snapshot endpoint (`/skills/market-snapshot`) with one or more token queries.
- The API resolves tokens + fetches pricing/metadata server-side (backed by Jupiter Tokens V2 + Price V3).
- Emits a **stable JSON object** (no prose) so other agents/bots can parse it reliably.

## What This Skill Will Not Do

- It will not create or manage wallets.
- It will not request, store, or handle private keys / seed phrases.
- It will not execute swaps or provide "trade recommendations".

## How To Use

When the user asks for prices, market snapshots, token metadata, or "what is X doing", run a snapshot.

Input formats supported:

- Symbols: `SOL`, `USDC`, `JUP`
- Names: `solana`, `jupiter`
- Mints: `So11111111111111111111111111111111111111112`

If multiple tokens are provided, resolve all of them and return a combined snapshot.

## Data Sources (GET, No Headers Needed)

- Market snapshot:
  - `https://app.vecstack.com/api/skills/market-snapshot?q=<CSV_TOKENS>&source=openclaw`

Examples (copy/paste):

- Single token:
  - `https://app.vecstack.com/api/skills/market-snapshot?q=SOL&source=openclaw`
- Multiple tokens (comma-separated, no spaces):
  - `https://app.vecstack.com/api/skills/market-snapshot?q=SOL,USDC,JUP&source=openclaw`

Notes:

- `web_fetch` caches by URL. If the user explicitly needs "fresh right now" data, append a cache-buster query param like `&_t=<unix>` to the URL.
- Do not invent values. If a fetch fails, keep `null` fields and include an entry in `warnings`/`errors`.

## Output Contract (Return JSON Only)

Return a single JSON object with this shape:

```json
{
  "as_of_unix": 0,
  "provider": "jupiter",
  "inputs": ["SOL", "USDC"],
  "tokens": [
    {
      "query": "SOL",
      "mint": "So11111111111111111111111111111111111111112",
      "symbol": "SOL",
      "name": "Wrapped SOL",
      "decimals": 9,
      "verified": true,
      "tags": [],
      "liquidity_usd": null,
      "mcap_usd": null,
      "fdv_usd": null,
      "usd_price": null,
      "price_change_24h_pct": null,
      "stats": {
        "5m": {
          "price_change_pct": null,
          "volume_usd": null,
          "buy_volume_usd": null,
          "sell_volume_usd": null
        },
        "1h": {
          "price_change_pct": null,
          "volume_usd": null,
          "buy_volume_usd": null,
          "sell_volume_usd": null
        },
        "24h": {
          "price_change_pct": null,
          "volume_usd": null,
          "buy_volume_usd": null,
          "sell_volume_usd": null
        }
      },
      "sources": {
        "token_search_url": null,
        "price_url": null
      }
    }
  ],
  "warnings": [],
  "errors": []
}
```

Field rules:

- `as_of_unix`: set to current Unix time when you finish assembling the response.
- `liquidity_usd`, `mcap_usd`, `fdv_usd`, and `stats.*` are populated from Tokens V2 search when present.
- `usd_price` and `price_change_24h_pct` are populated from Price V3 when present.
- `warnings`: non-fatal issues (missing price, ambiguous match, rate limits, etc).
- `errors`: fatal issues that prevented a snapshot (e.g., all sources failed).

## Implementation Notes For OpenClaw

- Prefer the `web_fetch` tool for the endpoint, using `extractMode=text` so the body stays parseable as JSON.
- If `web_fetch` returns non-JSON content, retry once with a cache-buster (append `&_t=<unix>`).
- Keep the final response strictly JSON.
