class AlertEngine {
  constructor(config) {
    this.config = config;
    this.alerts = config.alerts || [];
  }

  async checkAll(cryptoAPI, stockAPI) {
    const triggered = [];
    
    for (const alert of this.alerts) {
      if (alert.triggered) continue;
      
      try {
        let currentPrice;
        
        // Try crypto first, then stock
        try {
          const data = await cryptoAPI.getPrice(alert.symbol.toLowerCase());
          currentPrice = data.usd;
        } catch {
          const data = await stockAPI.getQuote(alert.symbol);
          currentPrice = data.price;
        }
        
        const result = this.checkAlert(alert, currentPrice);
        if (result.triggered) {
          triggered.push({
            ...alert,
            message: result.message,
            currentPrice
          });
          alert.triggered = true;
        }
      } catch (e) {
        console.log(`Failed to check alert for ${alert.symbol}: ${e.message}`);
      }
    }
    
    return triggered;
  }

  checkAlert(alert, currentPrice) {
    // Check price thresholds
    if (alert.above && currentPrice > alert.above) {
      return {
        triggered: true,
        message: `Price $${currentPrice.toLocaleString()} is above $${alert.above.toLocaleString()}`
      };
    }
    
    if (alert.below && currentPrice < alert.below) {
      return {
        triggered: true,
        message: `Price $${currentPrice.toLocaleString()} is below $${alert.below.toLocaleString()}`
      };
    }
    
    return { triggered: false };
  }
}

module.exports = AlertEngine;
