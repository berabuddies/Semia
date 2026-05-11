---
name: sparkbtcbot-proxy-deploy
description: Deploy a serverless Spark Bitcoin L2 proxy on Vercel with spending limits, auth, and Redis logging. Use when user wants to set up a new proxy, configure env vars, deploy to Vercel, or manage the proxy infrastructure.
argument-hint: "[Optional: setup, deploy, rotate-token, or configure]"
---

# Deploy sparkbtcbot-proxy

You are an expert in deploying and managing the sparkbtcbot-proxy — a serverless middleware that wraps the Spark Bitcoin L2 SDK behind authenticated REST endpoints on Vercel.

## What This Proxy Does

Gives AI agents scoped wallet access without exposing the mnemonic:
- Role-based token auth (`admin` for full access, `invoice` for read + create invoices only)
- Token management via API — create, list, revoke without redeploying
- Per-transaction and daily spending caps
- Activity logging to Redis
- Lazy detection of paid Lightning invoices

## What You Need

**Ask the user for these upfront:**

- Vercel account (free Hobby tier works)
- Upstash account email and API key (from https://console.upstash.com/account/api) — OR existing `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` if they already have a database
- BIP39 mnemonic for the Spark wallet (or generate one in step 3)
- Node.js 20+

**Generated during setup (don't ask for these):**

- `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` — created by the Upstash management API in step 2
- `API_AUTH_TOKEN` — generated in step 4

## Step-by-Step Deployment

### 1. Clone and install

```bash
git clone https://github.com/echennells/sparkbtcbot-proxy.git
cd sparkbtcbot-proxy
npm install
```

### 2. Create Upstash Redis

If the user already has `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN`, skip to step 3.

Otherwise, create a database via the Upstash API. The user needs their Upstash email and API key from https://console.upstash.com/account/api:

```bash
curl -X POST "https://api.upstash.com/v2/redis/database" \
  -u "UPSTASH_EMAIL:UPSTASH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "sparkbtcbot-proxy", "region": "global", "primary_region": "us-east-1"}'
```

**Note:** Regional database creation is deprecated. You must use `"region": "global"` with a `"primary_region"` field. The Upstash docs may not reflect this yet.

The response includes `rest_url` and `rest_token` — save these for step 5.

### 3. Generate a wallet mnemonic (if needed)

`SparkWallet.initialize()` returns `{ mnemonic, wallet }` when called without a mnemonic. One-liner:

```bash
node -e "import('@buildonspark/spark-sdk').then(({SparkWallet}) => SparkWallet.initialize({mnemonicOrSeed: null, options: {network: 'MAINNET'}}).then(r => { console.log(r.mnemonic); r.wallet.cleanupConnections() }))"
```

Save the 12-word mnemonic securely — it controls all funds in the wallet. There is no `getMnemonic()` method; you can only retrieve the mnemonic at initialization time.

Or use any BIP39 mnemonic generator. 12 or 24 words.

### 4. Generate an API auth token

```bash
openssl rand -base64 30
```

### 5. Deploy to Vercel

```bash
npx vercel --prod
```

When prompted, accept the defaults. Then set environment variables. All 7 are required:

| Variable | Description | Example |
|----------|-------------|---------|
| `SPARK_MNEMONIC` | 12-word BIP39 mnemonic | `fence connect trigger ...` |
| `SPARK_NETWORK` | Spark network | `MAINNET` |
| `API_AUTH_TOKEN` | Admin fallback bearer token | output of step 4 |
| `UPSTASH_REDIS_REST_URL` | Redis REST endpoint | `https://xxx.upstash.io` |
| `UPSTASH_REDIS_REST_TOKEN` | Redis auth token | from step 2 |
| `MAX_TRANSACTION_SATS` | Per-transaction spending cap | `10000` |
| `DAILY_BUDGET_SATS` | Daily spending cap (resets midnight UTC) | `100000` |

**Important:** Do NOT use `vercel env add` with heredoc/`<<<` input — it appends newlines that break the Spark SDK. Either use the Vercel dashboard or the REST API:

```bash
curl -X POST "https://api.vercel.com/v10/projects/<PROJECT_ID>/env?teamId=<TEAM_ID>" \
  -H "Authorization: Bearer <VERCEL_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"type":"encrypted","key":"SPARK_MNEMONIC","value":"your mnemonic here","target":["production","preview","development"]}'
```

Redeploy after setting env vars:

```bash
npx vercel --prod
```

### 6. Test

```bash
curl -H "Authorization: Bearer <your-token>" https://<your-deployment>.vercel.app/api/balance
```

Should return `{"success":true,"data":{"balance":"0","tokenBalances":{}}}`.

### 7. Create scoped tokens (optional)

Use the admin token to create limited tokens for agents:

```bash
curl -X POST -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"role": "invoice", "label": "my-agent"}' \
  https://<your-deployment>.vercel.app/api/tokens
```

The response includes the full token string — save it, it's only shown once. See the **Token Roles** section below for details.

## API Routes

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/llms.txt` | API documentation for bots (no auth required) |
| GET | `/api/balance` | Wallet balance (sats + tokens) |
| GET | `/api/info` | Spark address and identity pubkey |
| GET | `/api/transactions` | Transfer history (`?limit=&offset=`) |
| GET | `/api/deposit-address` | Bitcoin L1 deposit address |
| GET | `/api/fee-estimate` | Lightning send fee estimate (`?invoice=`) |
| GET | `/api/logs` | Recent activity logs (`?limit=`) |
| POST | `/api/invoice/create` | Create Lightning invoice (`{amountSats, memo?, expirySeconds?}`) |
| POST | `/api/invoice/spark` | Create Spark invoice (`{amount?, memo?}`) |
| POST | `/api/pay` | Pay Lightning invoice — admin only (`{invoice, maxFeeSats}`) |
| POST | `/api/transfer` | Spark transfer — admin only (`{receiverSparkAddress, amountSats}`) |
| POST | `/api/l402` | Pay L402 paywall — admin only (`{url, method?, headers?, body?, maxFeeSats?}`) |
| GET | `/api/l402/status` | Check/complete pending L402 (`?id=<pendingId>`) |
| GET | `/api/tokens` | List API tokens — admin only |
| POST | `/api/tokens` | Create a new token — admin only (`{role, label}`) |
| DELETE | `/api/tokens` | Revoke a token — admin only (`{token}`) |

## Token Roles

There are two token roles:

| Role | Permissions |
|------|------------|
| `admin` | Everything — read, create invoices, pay, transfer, manage tokens |
| `invoice` | Read (balance, info, transactions, logs, fee-estimate, deposit-address) + create invoices. Cannot pay or transfer. |

The `API_AUTH_TOKEN` env var is a hardcoded admin fallback — it always works even if Redis is down or tokens get wiped. Use it to bootstrap: create scoped tokens via the API, then hand those out to agents.

### Managing tokens

Create an invoice-only token for a merchant bot:

```bash
curl -X POST -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"role": "invoice", "label": "merchant-bot"}' \
  https://<deployment>/api/tokens
```

List all tokens (shows prefixes, labels, roles — not full token strings):

```bash
curl -H "Authorization: Bearer <admin-token>" https://<deployment>/api/tokens
```

Revoke a token:

```bash
curl -X DELETE -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"token": "<full-token-string>"}' \
  https://<deployment>/api/tokens
```

Tokens are stored in Redis (hash `spark:tokens`). They survive redeploys but not Redis flushes.

## L402 Paywall Support

The proxy can pay [L402](https://docs.lightning.engineering/the-lightning-network/l402) Lightning paywalls automatically. Send a URL, and the proxy will:

1. Fetch the URL
2. If 402 returned, parse the invoice and macaroon
3. Pay the Lightning invoice
4. Retry the request with the L402 Authorization header
5. Return the protected content

### Basic usage

```bash
curl -X POST -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://lightningfaucet.com/api/l402/joke"}' \
  https://<deployment>/api/l402
```

### Handling pending payments (important for agents)

Lightning payments via Spark are asynchronous. The proxy polls for up to ~7.5 seconds, but if the preimage isn't available in time, it returns a **pending** status:

```json
{
  "success": true,
  "data": {
    "status": "pending",
    "pendingId": "a1b2c3d4e5f6...",
    "message": "Payment sent but preimage not yet available. Poll GET /api/l402/status?id=<pendingId> to complete.",
    "priceSats": 21
  }
}
```

**Your agent MUST handle this case.** The payment has already been sent — if you don't poll for completion, you lose the sats without getting the content.

**Retry loop (pseudocode):**

```
response = POST /api/l402 { url: "..." }

if response.data.status == "pending":
    pendingId = response.data.pendingId
    for attempt in 1..10:
        sleep(3 seconds)
        status = GET /api/l402/status?id={pendingId}
        if status.data.status != "pending":
            return status.data  # Success or failure
    # Give up after ~30 seconds
    raise "L402 payment timed out"
else:
    return response.data  # Immediate success
```

**Key points:**
- **Token caching**: Paid L402 tokens are cached per-domain (up to 24 hours). Subsequent requests to the same domain reuse the cached token without paying again. If the token expires, the proxy pays for a new one automatically.
- Pending records expire after 1 hour
- The `/api/l402/status` endpoint polls Spark for up to 5 seconds per call
- If the payment failed on Spark's side, status will return an error
- Once complete, the pending record is deleted from Redis
- The proxy automatically retries the final fetch up to 3 times (200ms delay) if the response is empty — some servers don't return content immediately after payment

## Common Operations

### Rotate the admin fallback token

1. Generate a new token: `openssl rand -base64 30`
2. Update `API_AUTH_TOKEN` in Vercel env vars
3. Redeploy: `npx vercel --prod`
4. Update any agents using the old token

Redis-stored tokens are not affected by this — they continue working.

### Adjust spending limits

Update `MAX_TRANSACTION_SATS` and `DAILY_BUDGET_SATS` in Vercel env vars and redeploy. Budget resets daily at midnight UTC.

### Check logs

```bash
curl -H "Authorization: Bearer <token>" https://<deployment>/api/logs?limit=20
```

## Architecture

- **Vercel serverless functions** — each request spins up, initializes the Spark SDK (~1.5s), handles the request, and shuts down. No always-on process, no billing when idle.
- **Upstash Redis** — stores daily spend counters, activity logs, pending invoice tracking, and API tokens. Accessed over HTTP REST (no persistent connection needed). Free tier is limited to 1 database.
- **Spark SDK** — `@buildonspark/spark-sdk` connects to Spark Signing Operators via gRPC over HTTP/2. Pure JavaScript, no native addons.
- **Lazy invoice check** — on every request, the middleware checks Redis for pending invoices and compares against recent wallet transfers. Expired invoices are cleaned up, paid ones are logged. Max 5 checks per request, wrapped in try/catch so failures never affect the main request.
