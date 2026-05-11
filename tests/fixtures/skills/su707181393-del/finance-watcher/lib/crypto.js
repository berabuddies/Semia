const axios = require('axios');

class CryptoAPI {
  constructor() {
    this.baseURL = 'https://api.coingecko.com/api/v3';
    this.timeout = 10000;
  }

  async getPrice(id) {
    try {
      const response = await axios.get(`${this.baseURL}/simple/price`, {
        params: {
          ids: id,
          vs_currencies: 'usd',
          include_24hr_change: true
        },
        timeout: this.timeout
      });
      
      return response.data[id];
    } catch (error) {
      throw new Error(`Failed to fetch crypto price: ${error.message}`);
    }
  }

  async getPrices(ids) {
    try {
      const response = await axios.get(`${this.baseURL}/simple/price`, {
        params: {
          ids: ids.join(','),
          vs_currencies: 'usd',
          include_24hr_change: true
        },
        timeout: this.timeout
      });
      
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch crypto prices: ${error.message}`);
    }
  }

  async getTopCoins(limit = 10) {
    try {
      const response = await axios.get(`${this.baseURL}/coins/markets`, {
        params: {
          vs_currency: 'usd',
          order: 'market_cap_desc',
          per_page: limit,
          page: 1
        },
        timeout: this.timeout
      });
      
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch top coins: ${error.message}`);
    }
  }
}

module.exports = CryptoAPI;
