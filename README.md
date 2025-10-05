
# Crypto Trading Bot for Binance.US

A fully automated cryptocurrency trading bot for Binance.US with a Next.js dashboard for monitoring and control. Features momentum/trend-following strategy with strict risk management controls.

## 🚀 Features

### Trading Bot
- **Live Trading**: Real-time automated trading on Binance.US
- **Momentum/Trend Strategy**: Identifies high-momentum opportunities
- **Risk Management**: 
  - 2% risk per trade (configurable)
  - 15% daily loss limit (configurable)
  - Position sizing based on volatility
  - Maximum 3 concurrent positions
- **REST API**: Port 8889 for dashboard integration
- **24/7 Operation**: Designed for continuous trading

### Web Dashboard
- **Real-time Monitoring**: Live portfolio value and P&L
- **Position Management**: View and close active positions
- **Manual Trading**: Execute trades manually with full control
- **Risk Controls**: View and adjust risk parameters
- **Performance Analytics**: Track trading history and metrics
- **Emergency Stop**: Immediately halt all trading activity

## 📋 Prerequisites

- Python 3.10+
- Docker & Docker Compose
- Node.js 18+ (for dashboard)
- Binance.US account with API keys
- VPS or server with reliable internet connection

## 🔧 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/worldpath/Our-project-1.git
cd Our-project-1
```

### 2. Configure Environment Variables

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Binance.US API Credentials
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here

# Bot Configuration
TRADING_MODE=live  # or 'paper' for testing
CONFIG_FILE=config/ultra_aggressive.yaml

# API Server
API_HOST=0.0.0.0
API_PORT=8889
API_KEY=your_secure_api_key_here

# Risk Management
RISK_PER_TRADE=0.02  # 2% per trade
MAX_DAILY_LOSS=0.15   # 15% daily loss limit
MAX_POSITIONS=3
```

### 3. Deploy with Docker

```bash
# Start the bot
docker-compose up -d

# View logs
docker-compose logs -f crypto_bot

# Stop the bot
docker-compose down
```

### 4. Setup Dashboard (Optional)

The dashboard is deployed separately. See [Dashboard Setup](#dashboard-setup) below.

## 📊 Configuration

### Trading Configuration

Edit `config/ultra_aggressive.yaml` to customize:

```yaml
risk_management:
  risk_per_trade: 0.02
  max_daily_loss: 0.15
  max_positions: 3
  
strategy:
  momentum_threshold: 0.02
  volume_threshold_multiplier: 2.0
  
timeframes:
  - 5m
  - 15m
  - 1h
```

### Trading Pairs

The bot automatically loads available USDT pairs from Binance.US. You can also specify specific pairs in the config:

```yaml
trading_pairs:
  - BTCUSDT
  - ETHUSDT
  - SOLUSDT
```

## 🖥️ Dashboard Setup

### 1. Navigate to Dashboard Directory

The dashboard is in a separate repository or deployment:

```bash
cd /path/to/crypto_trading_dashboard
```

### 2. Configure Dashboard Environment

Create `nextjs_space/.env`:

```env
# Database
DATABASE_URL='postgresql://user:pass@host:port/db'

# Authentication
NEXTAUTH_SECRET=your_secret_here
NEXTAUTH_URL=https://your-dashboard-url.com

# VPS Bot Connection
VPS_API_URL=http://your_vps_ip:8889
VPS_API_KEY=your_bot_api_key_here
VPS_BOT_URL=http://your_vps_ip:8889

# Binance (optional - for direct calls)
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
```

### 3. Deploy Dashboard

```bash
cd nextjs_space
yarn install
yarn build
yarn start
```

## 🔌 API Endpoints

The bot exposes the following API endpoints on port 8889:

- `GET /health` - Bot health status
- `GET /status` - Detailed bot status and metrics
- `GET /positions` - Active trading positions
- `GET /balance` - Account balance
- `GET /config` - Current configuration
- `GET /pairs` - Available trading pairs
- `GET /trades` - Recent trades
- `POST /manual-trade` - Execute manual trade
- `POST /close-position` - Close a position
- `POST /emergency-stop` - Emergency stop all trading

All endpoints require the `X-API-Key` header with your configured API key.

## 🔒 Security

### API Key Protection

- Never commit `.env` files to version control
- Use strong, random API keys (32+ characters)
- Rotate API keys regularly
- Restrict Binance API key permissions (no withdrawals)

### Network Security

- Run bot on secure VPS with firewall
- Consider using VPN or IP whitelist for API access
- Use HTTPS for dashboard deployment
- Enable 2FA on Binance account

## 📈 Monitoring

### Bot Health

```bash
# Check if bot is running
docker-compose ps

# View real-time logs
docker-compose logs -f crypto_bot

# Check bot status via API
curl -H "X-API-Key: your_key" http://localhost:8889/status
```

### Dashboard

Access your deployed dashboard to monitor:
- Portfolio value and P&L
- Active positions
- Trading history
- Risk metrics

## 🛑 Emergency Procedures

### Stop Trading Immediately

```bash
# Via Dashboard
Click "Emergency Stop" button

# Via API
curl -X POST -H "X-API-Key: your_key" http://localhost:8889/emergency-stop

# Via Docker
docker-compose down
```

### Close All Positions

```bash
# Via Dashboard
Go to Positions page and close each position

# Via API
# Get positions first
curl -H "X-API-Key: your_key" http://localhost:8889/positions

# Close each position
curl -X POST -H "X-API-Key: your_key" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "BTCUSDT"}' \
  http://localhost:8889/close-position
```

## 📝 Troubleshooting

### Bot Not Starting

1. Check Docker logs: `docker-compose logs crypto_bot`
2. Verify `.env` file exists and has correct credentials
3. Test Binance API connection: `python test_binance_connection.py`
4. Ensure port 8889 is not in use: `lsof -i :8889`

### Dashboard Not Connecting

1. Verify VPS IP address in dashboard `.env`
2. Check bot API is accessible: `curl http://vps_ip:8889/health`
3. Verify API key matches between bot and dashboard
4. Check firewall rules allow port 8889

### No Trades Being Executed

1. Check market conditions (volatility, volume)
2. Review strategy parameters in config
3. Verify sufficient account balance
4. Check logs for any errors or warnings

## 🔄 Updates

### Update Bot Code

```bash
cd Our-project-1
git pull origin main
docker-compose down
docker-compose up -d --build
```

### Update Dashboard

```bash
cd crypto_trading_dashboard
git pull
cd nextjs_space
yarn install
yarn build
# Restart your deployment service
```

## 📚 Documentation

- [Deployment Guide](ENHANCED_DEPLOYMENT_GUIDE.md)
- [Configuration Guide](config/README.md)
- [API Documentation](docs/API.md)
- [Strategy Details](docs/STRATEGY.md)

## ⚠️ Disclaimer

**This bot is for educational purposes and personal use only.**

- Cryptocurrency trading involves substantial risk of loss
- Past performance does not guarantee future results
- Only trade with capital you can afford to lose
- The authors are not responsible for any trading losses
- Always test thoroughly in paper trading mode first

## 📧 Support

For issues and questions:
- Create an issue on GitHub
- Review the documentation
- Check existing issues and discussions

## 📄 License

[Add your license here]

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

**Current Status**: ✅ Bot is live on VPS at 207.246.99.168, connected to Binance.US, with API server running on port 8889.
