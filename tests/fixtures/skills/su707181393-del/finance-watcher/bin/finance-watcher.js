#!/usr/bin/env node

const { Command } = require('commander');
const chalk = require('chalk');
const fs = require('fs').promises;
const path = require('path');
const os = require('os');
const CryptoAPI = require('../lib/crypto');
const StockAPI = require('../lib/stock');
const AlertEngine = require('../lib/alerts');
const Reporter = require('../lib/reporter');

const program = new Command();
const CONFIG_DIR = path.join(os.homedir(), '.config', 'finance-watcher');
const CONFIG_FILE = path.join(CONFIG_DIR, 'config.json');

async function ensureConfig() {
  try {
    await fs.mkdir(CONFIG_DIR, { recursive: true });
    try {
      await fs.access(CONFIG_FILE);
    } catch {
      await fs.writeFile(CONFIG_FILE, JSON.stringify({
        watchlist: {
          crypto: ['bitcoin', 'ethereum', 'solana'],
          stocks: ['AAPL', 'TSLA', 'NVDA']
        },
        alerts: [],
        currency: 'USD',
        lastPrices: {}
      }, null, 2));
    }
  } catch (e) {
    console.error(chalk.red('Failed to create config:', e.message));
    process.exit(1);
  }
}

async function loadConfig() {
  await ensureConfig();
  const data = await fs.readFile(CONFIG_FILE, 'utf8');
  return JSON.parse(data);
}

async function saveConfig(config) {
  await fs.writeFile(CONFIG_FILE, JSON.stringify(config, null, 2));
}

program
  .name('finance-watcher')
  .description('Stock and crypto price monitoring with alerts')
  .version('1.0.0');

// Add to watchlist
program
  .command('add <symbol>')
  .description('Add symbol to watchlist (e.g., BTC, AAPL)')
  .option('-t, --type <type>', 'Type: crypto or stock', 'crypto')
  .action(async (symbol, options) => {
    const config = await loadConfig();
    const type = options.type.toLowerCase();
    
    if (!config.watchlist[type]) config.watchlist[type] = [];
    
    if (config.watchlist[type].includes(symbol.toUpperCase())) {
      console.log(chalk.yellow(`${symbol} already in watchlist`));
      return;
    }
    
    config.watchlist[type].push(symbol.toUpperCase());
    await saveConfig(config);
    console.log(chalk.green(`✓ Added ${symbol} to ${type} watchlist`));
  });

// Remove from watchlist
program
  .command('remove <symbol>')
  .description('Remove symbol from watchlist')
  .action(async (symbol) => {
    const config = await loadConfig();
    let removed = false;
    
    ['crypto', 'stocks'].forEach(type => {
      const idx = config.watchlist[type]?.indexOf(symbol.toUpperCase());
      if (idx > -1) {
        config.watchlist[type].splice(idx, 1);
        removed = true;
      }
    });
    
    if (removed) {
      await saveConfig(config);
      console.log(chalk.green(`✓ Removed ${symbol}`));
    } else {
      console.log(chalk.yellow(`${symbol} not found in watchlist`));
    }
  });

// List watchlist
program
  .command('list')
  .description('Show watchlist')
  .action(async () => {
    const config = await loadConfig();
    console.log(chalk.bold('\n📊 Watchlist\n'));
    
    console.log(chalk.cyan('Crypto:'));
    config.watchlist.crypto?.forEach(s => console.log(`  • ${s}`));
    
    console.log(chalk.cyan('\nStocks:'));
    config.watchlist.stocks?.forEach(s => console.log(`  • ${s}`));
  });

// Get prices
program
  .command('prices')
  .description('Get current prices for all watchlist items')
  .action(async () => {
    const config = await loadConfig();
    const crypto = new CryptoAPI();
    const stock = new StockAPI();
    
    console.log(chalk.blue('\n🔍 Fetching prices...\n'));
    
    // Crypto prices
    if (config.watchlist.crypto?.length > 0) {
      console.log(chalk.bold('Cryptocurrencies:'));
      console.log(chalk.gray('─'.repeat(50)));
      
      for (const symbol of config.watchlist.crypto) {
        try {
          const data = await crypto.getPrice(symbol.toLowerCase());
          const price = data?.usd || 'N/A';
          const change24h = data?.usd_24h_change;
          
          let changeStr = '';
          if (change24h !== undefined) {
            const color = change24h >= 0 ? chalk.green : chalk.red;
            changeStr = color(` (${change24h > 0 ? '+' : ''}${change24h.toFixed(2)}%)`);
          }
          
          console.log(`${chalk.white(symbol.toUpperCase().padEnd(10))} $${price.toLocaleString()}${changeStr}`);
        } catch (e) {
          console.log(chalk.red(`${symbol}: Failed to fetch`));
        }
      }
    }
    
    // Stock prices
    if (config.watchlist.stocks?.length > 0) {
      console.log(chalk.bold('\nStocks:'));
      console.log(chalk.gray('─'.repeat(50)));
      
      for (const symbol of config.watchlist.stocks) {
        try {
          const data = await stock.getQuote(symbol);
          const price = data?.price || 'N/A';
          const change = data?.change;
          const changePercent = data?.changePercent;
          
          let changeStr = '';
          if (change !== undefined) {
            const color = change >= 0 ? chalk.green : chalk.red;
            changeStr = color(` (${change > 0 ? '+' : ''}$${change.toFixed(2)} ${changePercent > 0 ? '+' : ''}${changePercent.toFixed(2)}%)`);
          }
          
          console.log(`${chalk.white(symbol.padEnd(10))} $${price.toLocaleString()}${changeStr}`);
        } catch (e) {
          console.log(chalk.red(`${symbol}: Failed to fetch`));
        }
      }
    }
    
    console.log();
  });

// Set price alert
program
  .command('alert <symbol>')
  .description('Set price alert (e.g., alert BTC --above 50000)')
  .option('-a, --above <price>', 'Alert when price goes above')
  .option('-b, --below <price>', 'Alert when price goes below')
  .option('-p, --percent <percent>', 'Alert on % change (e.g., 5 for 5%)')
  .action(async (symbol, options) => {
    if (!options.above && !options.below && !options.percent) {
      console.log(chalk.yellow('Please specify --above, --below, or --percent'));
      return;
    }
    
    const config = await loadConfig();
    config.alerts.push({
      id: Date.now().toString(),
      symbol: symbol.toUpperCase(),
      above: options.above ? parseFloat(options.above) : null,
      below: options.below ? parseFloat(options.below) : null,
      percent: options.percent ? parseFloat(options.percent) : null,
      createdAt: new Date().toISOString(),
      triggered: false
    });
    
    await saveConfig(config);
    console.log(chalk.green(`✓ Alert set for ${symbol}`));
  });

// Check alerts
program
  .command('check')
  .description('Check all alerts against current prices')
  .action(async () => {
    const config = await loadConfig();
    const alerts = new AlertEngine(config);
    const crypto = new CryptoAPI();
    const stock = new StockAPI();
    
    console.log(chalk.blue('\n🔔 Checking alerts...\n'));
    
    const triggered = await alerts.checkAll(crypto, stock);
    
    if (triggered.length === 0) {
      console.log(chalk.gray('No alerts triggered.'));
    } else {
      triggered.forEach(alert => {
        console.log(chalk.yellow(`⚠️  ${alert.symbol}: ${alert.message}`));
      });
    }
  });

// Generate report
program
  .command('report')
  .description('Generate portfolio report')
  .option('-o, --output <file>', 'Save to file')
  .action(async (options) => {
    const config = await loadConfig();
    const reporter = new Reporter(config);
    const crypto = new CryptoAPI();
    const stock = new StockAPI();
    
    console.log(chalk.blue('\n📈 Generating report...\n'));
    
    const report = await reporter.generate(crypto, stock);
    
    if (options.output) {
      await fs.writeFile(options.output, report);
      console.log(chalk.green(`✓ Report saved to: ${options.output}`));
    } else {
      console.log(report);
    }
  });

program.parse();
