# Optimized Trading Bot Deployment Instructions

## 📦 Package Contents
- `bot-optimized.cjs` - Optimized trading bot with full strategies
- `deploy-optimized-bot.sh` - Automated deployment script

## 🎯 What's New in This Version

### Performance Improvements
- **Trade scanning**: 120s → 15s (8x faster)
- **Position monitoring**: 60s → 30s (2x faster)
- **Market coverage**: 4 → 10 trading pairs

### New Trading Pairs Added
- XRP/USD
- ADA/USD
- DOGE/USD
- MATIC/USD
- LINK/USD
- DOT/USD

### Complete Trading Strategies
1. **Scalping** (35%) - Exploits short-term volatility
2. **Momentum** (25%) - Follows strong trends
3. **Mean Reversion** (20%) - Buys dips, sells rallies
4. **RSI** (10%) - Oversold/overbought signals
5. **MACD** (10%) - Trend crossovers

### Technical Indicators
- Real-time RSI calculation
- MACD with signal line
- Volatility tracking
- Momentum scoring
- 100-point price history per symbol

## 🚀 Deployment Steps

### Step 1: Upload Package to VPS
**Run on your MacOS:**
```bash
scp bot-optimized-deployment.tar.gz root@159.65.77.109:/tmp/
```

### Step 2: Extract Package
**Run on VPS:**
```bash
cd /tmp
tar -xzf bot-optimized-deployment.tar.gz
```

### Step 3: Deploy (Automated)
**Run on VPS:**
```bash
bash /tmp/deploy-optimized-bot.sh
```

This script will:
1. ✅ Backup your current bot
2. ✅ Stop the running bot
3. ✅ Deploy the optimized version
4. ✅ Restart the bot
5. ✅ Show logs to verify it's working

### Step 4: Verify Operation
**Run on VPS:**
```bash
pm2 logs trading-bot --lines 50
```

**Look for these indicators:**
- ✅ "Connected to [SYMBOL] price stream" (should see 10 symbols)
- ✅ "Running trading cycle..." every 15 seconds
- ✅ "Best opportunity: [SYMBOL]" when signals detected
- ✅ "Buying..." or "No strong buy signals detected"

## 🔍 Monitoring Commands

### Check Bot Status
```bash
pm2 status
```

### View Live Logs
```bash
pm2 logs trading-bot
```

### View Recent Logs (Last 50 lines)
```bash
pm2 logs trading-bot --lines 50 --nostream
```

### Check Dashboard
```bash
pm2 logs trading-dashboard --lines 20
```

### Restart Services (if needed)
```bash
pm2 restart trading-bot trading-dashboard
```

## ⚠️ Important Notes

### Before Deployment
- ✅ Ensure IP ban has lifted (after 11:21 AM PST)
- ✅ Verify you have sufficient balance for trading
- ✅ Current bot will be automatically backed up

### After Deployment
- Monitor logs for the first 5-10 minutes
- Verify WebSocket connections are stable
- Check that trading signals are being generated
- Ensure no API rate limit errors

### Rate Limit Safety
With WebSocket streaming, your REST API usage is minimal:
- Balance checks: ~1 per 5 minutes
- Trade execution: Only when signals trigger
- Position checks: No API calls (uses cached data)

**Estimated API usage**: 5-15 calls/minute (well under 1,200 weight/minute limit)

## 🎯 Expected Behavior

### Every 15 Seconds
- Bot evaluates all 10 symbols
- Calculates technical indicators
- Generates aggregated signals
- Executes best opportunity (if score > 0.4)

### Every 30 Seconds
- Checks all open positions
- Evaluates profit targets (2%)
- Evaluates stop losses (2%)
- Evaluates trailing stops (1.5%)

### Continuous (WebSocket)
- Real-time price updates
- Price history tracking
- Volatility calculation
- No REST API calls

## 📊 Configuration Details

Current settings in `bot-optimized.cjs`:
```javascript
tradeInterval: 15000,           // 15 seconds
positionCheckInterval: 30000,   // 30 seconds
profitTarget: 0.02,             // 2%
stopLoss: 0.02,                 // 2%
trailingStopPercent: 0.015,     // 1.5%
maxPositionSize: 0.15,          // 15% of equity per position
reservePercent: 0.10,           // Keep 10% in cash
minTradeSize: 10                // Minimum $10 per trade
```

## 🔧 Troubleshooting

### If WebSocket Connections Fail
```bash
pm2 restart trading-bot
pm2 logs trading-bot --lines 30
```

### If No Trades Are Executing
- Check available capital: Should show in logs
- Verify signals are being generated
- Ensure positions haven't hit max size (15% per symbol)

### If API Errors Occur
- Check if ban has fully lifted
- Verify API keys are valid
- Restart bot: `pm2 restart trading-bot`

## 📈 Next Steps After Deployment

1. Monitor for 15-30 minutes to ensure stability
2. Verify trades are executing when signals appear
3. Check dashboard shows real-time data
4. Push code to GitHub for backup

## 🆘 Rollback (If Needed)

If you need to revert to the previous version:
```bash
# Find your backup
ls -lt /opt/trading-bot/bot-backup-*

# Restore it (use the most recent backup filename)
cp /opt/trading-bot/bot-backup-YYYYMMDD-HHMMSS.cjs /opt/trading-bot/bot.cjs

# Restart
pm2 restart trading-bot
```

## ✅ Success Indicators

You'll know the deployment is successful when you see:
1. All 10 WebSocket connections established
2. Trading cycles running every 15 seconds
3. Position checks every 30 seconds
4. Technical indicators being calculated
5. Buy signals triggering when opportunities appear
6. No API rate limit errors

---

**Ready to deploy!** Just wait for the ban to lift at 11:21 AM PST, then run the commands above.
