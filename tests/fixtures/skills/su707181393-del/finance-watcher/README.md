# Finance Watcher

Stock and crypto price monitoring with alerts and reports.

## Install

```bash
npm install
```

## Usage

```bash
# Add assets
finance-watcher add bitcoin --type crypto
finance-watcher add TSLA --type stock

# Check prices
finance-watcher prices

# Set alerts
finance-watcher alert bitcoin --above 50000

# Generate report
finance-watcher report
```
