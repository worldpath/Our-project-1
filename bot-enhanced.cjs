const ccxt = require('ccxt');
const fs = require('fs');
const path = require('path');
const WebSocket = require('ws');

const CONFIG = {
  exchange: 'binanceus',
  apiKey: 'u3xWfmbbkcuouo2EfY416zzxDrARs6kJEfPx4y3Tq0lTPG0S1bjDb4o1UJnYGuRZ',
  apiSecret: 'pJOUr8CkDHVKcf9dsG51Ca2xADZ2PlPOW10IV7y2fdC6bkhZQAlxTt2ZNsUyFnZA',
  symbols: ['BTC/USD', 'ETH/USD', 'SOL/USD', 'AVAX/USD', 'XRP/USD', 'ADA/USD', 'DOGE/USD', 'MATIC/USD', 'LINK/USD', 'DOT/USD'],
  strategies: { scalping: 0.35, momentum: 0.25, meanReversion: 0.20, rsi: 0.10, macd: 0.10 },
  tradeInterval: 15000, // 15 seconds
  positionCheckInterval: 30000, // 30 seconds
  profitTarget: 0.02,
  stopLoss: 0.02,
  trailingStopPercent: 0.015,
  maxDrawdown: 0.10,
  minTradeSize: 10,
  reservePercent: 0.10,
  maxPositionSize: 0.15, // Max 15% of equity per position
  volatilityWindow: 20,
  // NEW: Dynamic position sizing
  basePositionSize: 0.10, // 10% base allocation
  volatilityMultiplier: 2.0, // Increase size in low volatility
  minVolatilityThreshold: 1.0, // Below this = low volatility
  maxVolatilityThreshold: 5.0, // Above this = high volatility
  // NEW: Volume confirmation
  volumeConfirmationEnabled: true,
  volumeThreshold: 1.2, // Require 20% above average volume
  // NEW: Limit orders
  useLimitOrders: true,
  limitOrderSlippage: 0.001, // 0.1% price improvement for limit orders
  limitOrderTimeout: 30000 // Cancel unfilled limit orders after 30 seconds
};

const TRADES_FILE = path.join(__dirname, 'trades.csv');
const POSITIONS_FILE = path.join(__dirname, 'positions.json');

let currentPrices = {};
let priceHistory = {}; // Track price history for technical indicators
let currentBalance = null;
let lastBalanceUpdate = 0;
const BALANCE_CACHE_MS = 300000; // Cache balance for 5 minutes
let pendingLimitOrders = {}; // Track pending limit orders

const exchange = new ccxt.binanceus({
  apiKey: CONFIG.apiKey,
  secret: CONFIG.apiSecret,
  enableRateLimit: true,
  options: { defaultType: 'spot' }
});

function connectPriceStream(symbol) {
  const wsSymbol = symbol.replace('/', '').toLowerCase();
  const wsUrl = `wss://stream.binance.us:9443/ws/${wsSymbol}@ticker`;
  
  const ws = new WebSocket(wsUrl);
  
  ws.on('open', () => console.log(`📡 Connected to ${symbol} price stream`));
  
  ws.on('message', (data) => {
    try {
      const ticker = JSON.parse(data);
      const price = parseFloat(ticker.c);
      const volume = parseFloat(ticker.v || 0);
      currentPrices[symbol] = price;
      
      // Track price history for technical analysis
      if (!priceHistory[symbol]) priceHistory[symbol] = [];
      priceHistory[symbol].push({
        price: price,
        timestamp: Date.now(),
        volume: volume
      });
      
      // Keep only recent history (last 100 data points)
      if (priceHistory[symbol].length > 100) {
        priceHistory[symbol].shift();
      }
    } catch (error) {
      console.error(`Error parsing ${symbol}:`, error.message);
    }
  });
  
  ws.on('error', (error) => console.error(`WebSocket error ${symbol}:`, error.message));
  
  ws.on('close', () => {
    console.log(`📴 ${symbol} stream closed, reconnecting in 5s...`);
    setTimeout(() => connectPriceStream(symbol), 5000);
  });
}

async function getBalance() {
  const now = Date.now();
  if (currentBalance && (now - lastBalanceUpdate) < BALANCE_CACHE_MS) {
    return currentBalance;
  }
  
  try {
    const balance = await exchange.fetchBalance();
    currentBalance = {
      USD: parseFloat(balance.free['USD'] || 0),
      USDT: parseFloat(balance.free['USDT'] || 0),
      BTC: parseFloat(balance.free['BTC'] || 0),
      ETH: parseFloat(balance.free['ETH'] || 0),
      SOL: parseFloat(balance.free['SOL'] || 0),
      AVAX: parseFloat(balance.free['AVAX'] || 0),
      XRP: parseFloat(balance.free['XRP'] || 0),
      ADA: parseFloat(balance.free['ADA'] || 0),
      DOGE: parseFloat(balance.free['DOGE'] || 0),
      MATIC: parseFloat(balance.free['MATIC'] || 0),
      LINK: parseFloat(balance.free['LINK'] || 0),
      DOT: parseFloat(balance.free['DOT'] || 0)
    };
    lastBalanceUpdate = now;
    return currentBalance;
  } catch (error) {
    console.error('❌ Balance error:', error.message);
    return currentBalance || { USD: 0, USDT: 0, BTC: 0, ETH: 0, SOL: 0, AVAX: 0, XRP: 0, ADA: 0, DOGE: 0, MATIC: 0, LINK: 0, DOT: 0 };
  }
}

function getCurrentPrice(symbol) {
  return currentPrices[symbol] || 0;
}

function loadPositions() {
  try {
    if (fs.existsSync(POSITIONS_FILE)) {
      return JSON.parse(fs.readFileSync(POSITIONS_FILE, 'utf8'));
    }
  } catch (error) {
    console.error('Error loading positions:', error.message);
  }
  return {};
}

function savePositions(positions) {
  try {
    fs.writeFileSync(POSITIONS_FILE, JSON.stringify(positions, null, 2));
  } catch (error) {}
}

function logTrade(trade) {
  const timestamp = Date.now();
  const date = new Date(timestamp).toISOString();
  const pnl = trade.pnl || '';
  const row = `${timestamp},${date},${trade.side},${trade.symbol},${trade.amount},${trade.price},${trade.usdValue},${trade.orderId},${trade.strategy},${pnl}\n`;
  
  if (!fs.existsSync(TRADES_FILE)) {
    fs.writeFileSync(TRADES_FILE, 'Timestamp,Date,Type,Symbol,Quantity,Price,USD_Value,Order_ID,Strategy,PnL\n');
  }
  fs.appendFileSync(TRADES_FILE, row);
}

// Technical Analysis Functions
function calculateRSI(symbol, period = 14) {
  const history = priceHistory[symbol];
  if (!history || history.length < period + 1) return 50;
  
  const prices = history.slice(-period - 1).map(h => h.price);
  let gains = 0, losses = 0;
  
  for (let i = 1; i < prices.length; i++) {
    const change = prices[i] - prices[i - 1];
    if (change > 0) gains += change;
    else losses += Math.abs(change);
  }
  
  const avgGain = gains / period;
  const avgLoss = losses / period;
  
  if (avgLoss === 0) return 100;
  const rs = avgGain / avgLoss;
  return 100 - (100 / (1 + rs));
}

function calculateMACD(symbol) {
  const history = priceHistory[symbol];
  if (!history || history.length < 26) return { macd: 0, signal: 0, histogram: 0 };
  
  const prices = history.map(h => h.price);
  const ema12 = calculateEMA(prices, 12);
  const ema26 = calculateEMA(prices, 26);
  const macd = ema12 - ema26;
  const signal = macd * 0.2;
  const histogram = macd - signal;
  
  return { macd, signal, histogram };
}

function calculateEMA(prices, period) {
  const k = 2 / (period + 1);
  let ema = prices[0];
  
  for (let i = 1; i < prices.length; i++) {
    ema = prices[i] * k + ema * (1 - k);
  }
  
  return ema;
}

function calculateVolatility(symbol) {
  const history = priceHistory[symbol];
  if (!history || history.length < CONFIG.volatilityWindow) return 0;
  
  const recentPrices = history.slice(-CONFIG.volatilityWindow).map(h => h.price);
  const mean = recentPrices.reduce((a, b) => a + b, 0) / recentPrices.length;
  const variance = recentPrices.reduce((sum, price) => sum + Math.pow(price - mean, 2), 0) / recentPrices.length;
  const stdDev = Math.sqrt(variance);
  
  return (stdDev / mean) * 100;
}

function calculateMomentum(symbol, period = 10) {
  const history = priceHistory[symbol];
  if (!history || history.length < period) return 0;
  
  const currentPrice = history[history.length - 1].price;
  const pastPrice = history[history.length - period].price;
  
  return ((currentPrice - pastPrice) / pastPrice) * 100;
}

// NEW: Volume analysis
function getAverageVolume(symbol, period = 20) {
  const history = priceHistory[symbol];
  if (!history || history.length < period) return 0;
  
  const recentVolumes = history.slice(-period).map(h => h.volume);
  return recentVolumes.reduce((a, b) => a + b, 0) / recentVolumes.length;
}

function getCurrentVolume(symbol) {
  const history = priceHistory[symbol];
  if (!history || history.length === 0) return 0;
  return history[history.length - 1].volume;
}

function isVolumeConfirmed(symbol) {
  if (!CONFIG.volumeConfirmationEnabled) return true;
  
  const currentVol = getCurrentVolume(symbol);
  const avgVol = getAverageVolume(symbol);
  
  if (avgVol === 0) return true; // No data, allow trade
  
  const volumeRatio = currentVol / avgVol;
  return volumeRatio >= CONFIG.volumeThreshold;
}

// NEW: Dynamic position sizing based on volatility
function calculateDynamicPositionSize(symbol, totalEquity) {
  const volatility = calculateVolatility(symbol);
  
  let positionSize = CONFIG.basePositionSize;
  
  // Adjust based on volatility
  if (volatility < CONFIG.minVolatilityThreshold) {
    // Low volatility = increase position size
    positionSize *= CONFIG.volatilityMultiplier;
  } else if (volatility > CONFIG.maxVolatilityThreshold) {
    // High volatility = decrease position size
    positionSize *= (1 / CONFIG.volatilityMultiplier);
  }
  
  // Cap at max position size
  positionSize = Math.min(positionSize, CONFIG.maxPositionSize);
  
  const usdAmount = totalEquity * positionSize;
  
  console.log(`   📊 Dynamic sizing: Volatility=${volatility.toFixed(2)}% → Position=${(positionSize*100).toFixed(1)}% ($${usdAmount.toFixed(2)})`);
  
  return usdAmount;
}

// Trading Strategy Functions
function scalpingSignal(symbol) {
  const volatility = calculateVolatility(symbol);
  const momentum = calculateMomentum(symbol, 5);
  
  if (volatility > 2 && momentum > 0.5) return { signal: 'BUY', confidence: 0.7 };
  if (volatility > 2 && momentum < -0.5) return { signal: 'SELL', confidence: 0.7 };
  
  return { signal: 'HOLD', confidence: 0 };
}

function momentumSignal(symbol) {
  const momentum = calculateMomentum(symbol, 10);
  const shortMomentum = calculateMomentum(symbol, 5);
  
  if (momentum > 1.5 && shortMomentum > momentum * 0.5) return { signal: 'BUY', confidence: 0.8 };
  if (momentum < -1.5 && shortMomentum < momentum * 0.5) return { signal: 'SELL', confidence: 0.8 };
  
  return { signal: 'HOLD', confidence: 0 };
}

function meanReversionSignal(symbol) {
  const history = priceHistory[symbol];
  if (!history || history.length < 20) return { signal: 'HOLD', confidence: 0 };
  
  const recentPrices = history.slice(-20).map(h => h.price);
  const mean = recentPrices.reduce((a, b) => a + b, 0) / recentPrices.length;
  const currentPrice = getCurrentPrice(symbol);
  const deviation = ((currentPrice - mean) / mean) * 100;
  
  if (deviation < -2) return { signal: 'BUY', confidence: 0.6 };
  if (deviation > 2) return { signal: 'SELL', confidence: 0.6 };
  
  return { signal: 'HOLD', confidence: 0 };
}

function rsiSignal(symbol) {
  const rsi = calculateRSI(symbol);
  
  if (rsi < 30) return { signal: 'BUY', confidence: 0.75 };
  if (rsi > 70) return { signal: 'SELL', confidence: 0.75 };
  
  return { signal: 'HOLD', confidence: 0 };
}

function macdSignal(symbol) {
  const { macd, signal, histogram } = calculateMACD(symbol);
  
  if (histogram > 0 && macd > signal) return { signal: 'BUY', confidence: 0.65 };
  if (histogram < 0 && macd < signal) return { signal: 'SELL', confidence: 0.65 };
  
  return { signal: 'HOLD', confidence: 0 };
}

function getAggregatedSignal(symbol) {
  const signals = {
    scalping: scalpingSignal(symbol),
    momentum: momentumSignal(symbol),
    meanReversion: meanReversionSignal(symbol),
    rsi: rsiSignal(symbol),
    macd: macdSignal(symbol)
  };
  
  let buyScore = 0, sellScore = 0;
  
  for (const [strategy, weight] of Object.entries(CONFIG.strategies)) {
    const signal = signals[strategy];
    if (signal.signal === 'BUY') buyScore += weight * signal.confidence;
    if (signal.signal === 'SELL') sellScore += weight * signal.confidence;
  }
  
  // NEW: Volume confirmation
  const volumeConfirmed = isVolumeConfirmed(symbol);
  if (!volumeConfirmed) {
    console.log(`   ⚠️ ${symbol}: Signal detected but volume too low (${(getCurrentVolume(symbol) / getAverageVolume(symbol)).toFixed(2)}x avg)`);
    return { action: 'HOLD', score: 0, signals, volumeConfirmed: false };
  }
  
  if (buyScore > 0.4) return { action: 'BUY', score: buyScore, signals, volumeConfirmed: true };
  if (sellScore > 0.4) return { action: 'SELL', score: sellScore, signals, volumeConfirmed: true };
  
  return { action: 'HOLD', score: 0, signals, volumeConfirmed: true };
}

// NEW: Limit order execution
async function executeBuyLimit(symbol, usdAmount, strategy) {
  try {
    const currentPrice = getCurrentPrice(symbol);
    // Place limit order slightly below current price for better fill
    const limitPrice = currentPrice * (1 - CONFIG.limitOrderSlippage);
    const amount = usdAmount / limitPrice;
    
    console.log(`🟢 Placing BUY LIMIT ${amount.toFixed(6)} ${symbol} @ $${limitPrice.toFixed(2)} | Strategy: ${strategy} | USD: $${usdAmount.toFixed(2)}`);
    
    let order;
    const usdtSymbol = symbol.replace('/USD', '/USDT');
    
    try {
      order = await exchange.createLimitBuyOrder(usdtSymbol, amount, limitPrice);
    } catch (e) {
      order = await exchange.createLimitBuyOrder(symbol, amount, limitPrice);
    }
    
    // Track pending order
    pendingLimitOrders[order.id] = {
      symbol,
      side: 'BUY',
      amount,
      price: limitPrice,
      usdAmount,
      strategy,
      timestamp: Date.now()
    };
    
    console.log(`   ⏳ Limit order placed: ${order.id}`);
    
    // Set timeout to check/cancel order
    setTimeout(() => checkLimitOrder(order.id), CONFIG.limitOrderTimeout);
    
    return true;
  } catch (error) {
    console.error(`❌ Buy limit error ${symbol}:`, error.message);
    return false;
  }
}

async function checkLimitOrder(orderId) {
  if (!pendingLimitOrders[orderId]) return; // Already processed
  
  try {
    const order = await exchange.fetchOrder(orderId);
    const orderInfo = pendingLimitOrders[orderId];
    
    if (order.status === 'closed' || order.status === 'filled') {
      // Order filled successfully
      console.log(`✅ Limit order filled: ${orderId}`);
      
      const price = order.average || order.price;
      const actualAmount = order.filled;
      const usdValue = actualAmount * price;
      
      logTrade({
        side: 'BUY',
        symbol: orderInfo.symbol.replace('/', ''),
        amount: actualAmount,
        price,
        usdValue,
        orderId: order.id,
        strategy: orderInfo.strategy
      });
      
      const positions = loadPositions();
      const base = orderInfo.symbol.split('/')[0];
      
      if (!positions[base]) {
        positions[base] = { totalAmount: 0, totalCost: 0, highestPrice: price };
      }
      
      positions[base].totalAmount += actualAmount;
      positions[base].totalCost += usdValue;
      positions[base].highestPrice = Math.max(positions[base].highestPrice || 0, price);
      
      savePositions(positions);
      lastBalanceUpdate = 0;
      
      delete pendingLimitOrders[orderId];
    } else if (order.status === 'open') {
      // Order still pending, cancel it
      console.log(`⏰ Limit order timeout, canceling: ${orderId}`);
      await exchange.cancelOrder(orderId);
      delete pendingLimitOrders[orderId];
    }
  } catch (error) {
    console.error(`❌ Error checking limit order ${orderId}:`, error.message);
    delete pendingLimitOrders[orderId];
  }
}

async function executeBuy(symbol, usdAmount, strategy) {
  if (CONFIG.useLimitOrders) {
    return await executeBuyLimit(symbol, usdAmount, strategy);
  }
  
  // Fallback to market order
  try {
    const currentPrice = getCurrentPrice(symbol);
    const amount = usdAmount / currentPrice;
    
    console.log(`🟢 Buying ${amount.toFixed(6)} ${symbol} @ $${currentPrice.toFixed(2)} | Strategy: ${strategy} | USD: $${usdAmount.toFixed(2)}`);
    
    let order;
    const usdtSymbol = symbol.replace('/USD', '/USDT');
    
    try {
      order = await exchange.createMarketBuyOrder(usdtSymbol, amount);
    } catch (e) {
      order = await exchange.createMarketBuyOrder(symbol, amount);
    }
    
    const price = order.average || order.price || currentPrice;
    const actualAmount = order.filled || amount;
    const usdValue = actualAmount * price;
    
    logTrade({
      side: 'BUY',
      symbol: symbol.replace('/', ''),
      amount: actualAmount,
      price,
      usdValue,
      orderId: order.id,
      strategy
    });
    
    const positions = loadPositions();
    const base = symbol.split('/')[0];
    
    if (!positions[base]) {
      positions[base] = { totalAmount: 0, totalCost: 0, highestPrice: price };
    }
    
    positions[base].totalAmount += actualAmount;
    positions[base].totalCost += usdValue;
    positions[base].highestPrice = Math.max(positions[base].highestPrice || 0, price);
    
    savePositions(positions);
    lastBalanceUpdate = 0;
    return true;
  } catch (error) {
    console.error(`❌ Buy error ${symbol}:`, error.message);
    return false;
  }
}

async function executeSell(symbol, amount, reason, avgBuyPrice) {
  try {
    const currentPrice = getCurrentPrice(symbol);
    const pnl = ((currentPrice - avgBuyPrice) / avgBuyPrice) * 100;
    const pnlUSD = (currentPrice - avgBuyPrice) * amount;
    
    console.log(`💰 Selling ${amount.toFixed(6)} ${symbol} @ $${currentPrice.toFixed(2)} (${reason}) | P&L: $${pnlUSD.toFixed(2)} (${pnl > 0 ? '+' : ''}${pnl.toFixed(2)}%)`);
    
    let order;
    const usdtSymbol = symbol.replace('/USD', '/USDT');
    
    try {
      order = await exchange.createMarketSellOrder(usdtSymbol, amount);
    } catch (e) {
      order = await exchange.createMarketSellOrder(symbol, amount);
    }
    
    const price = order.average || order.price || currentPrice;
    const usdValue = amount * price;
    
    logTrade({
      side: 'SELL',
      symbol: symbol.replace('/', ''),
      amount, price, usdValue,
      orderId: order.id,
      strategy: reason,
      pnl: pnlUSD
    });
    
    const positions = loadPositions();
    const base = symbol.split('/')[0];
    
    if (positions[base]) {
      positions[base].totalAmount -= amount;
      positions[base].totalCost -= (positions[base].totalCost / (positions[base].totalAmount + amount)) * amount;
      if (positions[base].totalAmount <= 0.001) delete positions[base];
      savePositions(positions);
    }
    
    lastBalanceUpdate = 0;
    return true;
  } catch (error) {
    console.error(`❌ Sell error ${symbol}:`, error.message);
    return false;
  }
}

async function checkPositions() {
  const positions = loadPositions();
  const balance = await getBalance();
  
  for (const [base, position] of Object.entries(positions)) {
    const symbol = `${base}/USD`;
    const currentPrice = getCurrentPrice(symbol);
    const currentHolding = balance[base] || 0;
    
    if (currentHolding < 0.0001 || currentPrice === 0) continue;
    
    const avgBuyPrice = position.totalCost / position.totalAmount;
    const pnlPercent = ((currentPrice - avgBuyPrice) / avgBuyPrice) * 100;
    
    console.log(`📊 ${base}: ${currentHolding.toFixed(6)} @ $${currentPrice.toFixed(2)} | Avg Buy: $${avgBuyPrice.toFixed(2)} | P&L: ${pnlPercent > 0 ? '+' : ''}${pnlPercent.toFixed(2)}%`);
    
    if (pnlPercent >= (CONFIG.profitTarget * 100)) {
      console.log(`🎯 Profit target hit for ${base}: +${pnlPercent.toFixed(2)}%`);
      await executeSell(symbol, currentHolding, 'Profit Target', avgBuyPrice);
      continue;
    }
    
    if (pnlPercent <= -(CONFIG.stopLoss * 100)) {
      console.log(`🛑 Stop loss hit for ${base}: ${pnlPercent.toFixed(2)}%`);
      await executeSell(symbol, currentHolding, 'Stop Loss', avgBuyPrice);
      continue;
    }
    
    if (position.highestPrice) {
      const dropFromPeak = ((position.highestPrice - currentPrice) / position.highestPrice) * 100;
      if (dropFromPeak >= (CONFIG.trailingStopPercent * 100) && currentPrice > avgBuyPrice) {
        console.log(`📉 Trailing stop hit for ${base}: -${dropFromPeak.toFixed(2)}% from peak`);
        await executeSell(symbol, currentHolding, 'Trailing Stop', avgBuyPrice);
        continue;
      }
      if (currentPrice > position.highestPrice) {
        position.highestPrice = currentPrice;
        savePositions(positions);
      }
    }
  }
}

async function tradingLoop() {
  try {
    const balance = await getBalance();
    const totalCash = balance.USD + balance.USDT;
    
    let cryptoValue = 0;
    for (const symbol of CONFIG.symbols) {
      const base = symbol.split('/')[0];
      cryptoValue += (balance[base] || 0) * getCurrentPrice(symbol);
    }
    
    const totalEquity = totalCash + cryptoValue;
    console.log(`\n🔄 Running trading cycle...`);
    console.log(`💰 Total Equity: $${totalEquity.toFixed(2)} | Cash: $${totalCash.toFixed(2)} | Crypto: $${cryptoValue.toFixed(2)}`);
    
    const availableCapital = Math.max(0, totalCash - (totalEquity * CONFIG.reservePercent));
    if (availableCapital < CONFIG.minTradeSize) {
      console.log(`⚠️ Insufficient capital: $${availableCapital.toFixed(2)}`);
      return;
    }
    
    const opportunities = [];
    
    for (const symbol of CONFIG.symbols) {
      const currentPrice = getCurrentPrice(symbol);
      if (currentPrice === 0) continue;
      
      const signal = getAggregatedSignal(symbol);
      
      if (signal.action === 'BUY' && signal.volumeConfirmed) {
        const base = symbol.split('/')[0];
        const currentPosition = (balance[base] || 0) * currentPrice;
        const maxPositionValue = totalEquity * CONFIG.maxPositionSize;
        
        if (currentPosition < maxPositionValue) {
          opportunities.push({
            symbol,
            action: 'BUY',
            score: signal.score,
            signals: signal.signals
          });
        }
      }
    }
    
    opportunities.sort((a, b) => b.score - a.score);
    
    if (opportunities.length > 0) {
      const best = opportunities[0];
      // NEW: Dynamic position sizing
      const tradeSize = Math.min(
        calculateDynamicPositionSize(best.symbol, totalEquity),
        availableCapital * 0.5 // Don't use more than 50% of available capital
      );
      
      console.log(`🎯 Best opportunity: ${best.symbol} (Score: ${best.score.toFixed(2)})`);
      console.log(`   Signals: Scalping=${best.signals.scalping.signal}, Momentum=${best.signals.momentum.signal}, MeanRev=${best.signals.meanReversion.signal}, RSI=${best.signals.rsi.signal}, MACD=${best.signals.macd.signal}`);
      
      await executeBuy(best.symbol, tradeSize, 'Multi-Strategy');
    } else {
      console.log(`📊 No strong buy signals detected`);
    }
    
  } catch (error) {
    console.error('❌ Trading loop error:', error.message);
  }
}

async function main() {
  console.log('🤖 Binance.US Trading Bot Starting (Enhanced Mode)...');
  console.log(`📊 Trading pairs: ${CONFIG.symbols.join(', ')}`);
  console.log(`🎯 Profit Target: ${(CONFIG.profitTarget * 100).toFixed(1)}%`);
  console.log(`🛑 Stop Loss: ${(CONFIG.stopLoss * 100).toFixed(1)}%`);
  console.log(`📉 Trailing Stop: ${(CONFIG.trailingStopPercent * 100).toFixed(1)}%`);
  console.log(`⚡ Trade Interval: ${CONFIG.tradeInterval / 1000}s`);
  console.log(`🔍 Position Check: ${CONFIG.positionCheckInterval / 1000}s`);
  console.log(`📡 Using WebSocket streams for live prices`);
  console.log(`💾 Balance cached for 5 minutes`);
  console.log(`\n✨ ENHANCEMENTS:`);
  console.log(`   📊 Dynamic position sizing (${(CONFIG.basePositionSize*100).toFixed(0)}% base, volatility-adjusted)`);
  console.log(`   📈 Volume confirmation (${CONFIG.volumeThreshold}x average required)`);
  console.log(`   💱 Limit orders enabled (${(CONFIG.limitOrderSlippage*100).toFixed(1)}% price improvement)\n`);
  
  for (const symbol of CONFIG.symbols) connectPriceStream(symbol);
  await new Promise(resolve => setTimeout(resolve, 3000));
  
  const positions = loadPositions();
  console.log(`📂 Loaded positions: ${Object.keys(positions).length}`);
  
  const balance = await getBalance();
  const totalCash = balance.USD + balance.USDT;
  let cryptoValue = 0;
  for (const symbol of CONFIG.symbols) {
    const base = symbol.split('/')[0];
    cryptoValue += (balance[base] || 0) * getCurrentPrice(symbol);
  }
  console.log(`💎 Starting Equity: $${(totalCash + cryptoValue).toFixed(2)}\n`);
  
  setInterval(tradingLoop, CONFIG.tradeInterval);
  tradingLoop();
  
  setInterval(checkPositions, CONFIG.positionCheckInterval);
  checkPositions();
}

main().catch(console.error);
