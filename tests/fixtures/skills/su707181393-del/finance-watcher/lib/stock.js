const axios = require('axios');

class StockAPI {
  constructor() {
    // Using Yahoo Finance API (unofficial but widely used)
    this.baseURL = 'https://query1.finance.yahoo.com/v8/finance/chart';
    this.timeout = 10000;
  }

  async getQuote(symbol) {
    try {
      const response = await axios.get(`${this.baseURL}/${symbol}`, {
        params: {
          interval: '1d',
          range: '1d'
        },
        timeout: this.timeout,
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
      });
      
      const result = response.data.chart?.result?.[0];
      if (!result) throw new Error('No data available');
      
      const meta = result.meta;
      const price = meta.regularMarketPrice;
      const prevClose = meta.previousClose || meta.chartPreviousClose;
      const change = price - prevClose;
      const changePercent = (change / prevClose) * 100;
      
      return {
        symbol: symbol.toUpperCase(),
        price: price,
        change: change,
        changePercent: changePercent,
        currency: meta.currency,
        marketTime: meta.regularMarketTime
      };
    } catch (error) {
      throw new Error(`Failed to fetch stock quote: ${error.message}`);
    }
  }

  async getQuotes(symbols) {
    const results = {};
    for (const symbol of symbols) {
      try {
        results[symbol] = await this.getQuote(symbol);
      } catch (e) {
        results[symbol] = { error: e.message };
      }
    }
    return results;
  }
}

module.exports = StockAPI;
