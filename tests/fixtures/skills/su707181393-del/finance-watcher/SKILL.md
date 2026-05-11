---
name: finance-watcher
description: Stock and cryptocurrency price monitoring with alerts and daily reports. Track your portfolio, set price alerts, and generate investment reports. No API key required.
metadata:
  {
    "openclaw":
      {
        "emoji": "📈",
        "requires": { "bins": ["node", "npm"] },
        "install":
          [
            {
              "id": "npm",
              "kind": "node",
              "package": "finance-watcher",
              "bins": ["finance-watcher"],
              "label": "Install Finance Watcher CLI",
            },
          ],
      },
  }
---

# Finance Watcher

Monitor stock and cryptocurrency prices with ease. Set alerts, track your portfolio, and generate daily reports.

## Features

- ✅ **Real-time Prices** - Crypto (CoinGecko) & Stocks (Yahoo Finance)
- ✅ **Price Alerts** - Get notified when prices hit your targets
- ✅ **Portfolio Tracking** - Watchlist for all your assets
- ✅ **Daily Reports** - Markdown reports with price changes
- ✅ **No API Key** - Free data sources, no registration needed

## Quick Start

```bash
# Install
npm install

# Add assets to watchlist
finance-watcher add BTC --type crypto
finance-watcher add AAPL --type stock

# Check current prices
finance-watcher prices

# Set an alert
finance-watcher alert BTC --above 50000

# Generate report
finance-watcher report --output daily-report.md
```

## Commands

| Command | Description |
|---------|-------------|
| `add <symbol>` | Add to watchlist (`--type crypto/stock`) |
| `remove <symbol>` | Remove from watchlist |
| `list` | Show watchlist |
| `prices` | Get current prices |
| `alert <symbol>` | Set price alert (`--above`, `--below`, `--percent`) |
| `check` | Check all alerts |
| `report` | Generate portfolio report |

## Data Sources

- **Crypto**: CoinGecko API (free, no key)
- **Stocks**: Yahoo Finance API (unofficial, free)

## Use Cases

1. **Personal Portfolio** - Track your investments daily
2. **Trading Alerts** - Never miss entry/exit points
3. **Market Research** - Compare crypto vs stock performance
4. **Automated Reports** - Schedule daily summaries

## Integration

Works great with:
- Cron jobs for scheduled checks
- Feishu/Slack webhooks for alerts
- Content Watcher for market news + price data combo
