#!/usr/bin/env python3
"""
Enhanced Trading Bot Startup Script
==================================

This script provides easy startup and management for the Ultra-Aggressive
Enhanced Crypto Trading Bot with all institutional-grade features.

Usage:
  python start_enhanced_bot.py [mode]
  
Modes:
  - live: Start live trading (default)
  - test: Start in test mode with testnet
  - backtest: Run backtesting only
  - monitor: Start monitoring dashboard only
  - setup: Initial setup and configuration check
"""

import sys
import os
import asyncio
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Ensure the project root is in Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from main_enhanced import UltraAgressiveTradingBot
from enhanced_backtesting import BacktestConfig, run_comprehensive_backtest
from enhanced_monitoring import setup_enhanced_monitoring

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedBotManager:
    """Manager for the Enhanced Trading Bot with multiple operation modes"""
    
    def __init__(self, mode: str = "live"):
        self.mode = mode
        self.bot = None
        
    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met for running the bot"""
        logger.info("🔍 Checking prerequisites...")
        
        # Check required files
        required_files = [
            "config/ultra_aggressive.yaml",
            ".env",
            "all_binance_usdt_pairs.json"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            logger.error(f"❌ Missing required files: {missing_files}")
            return False
        
        # Check required directories
        required_dirs = ["logs", "config", "tax_reports"]
        for dir_path in required_dirs:
            os.makedirs(dir_path, exist_ok=True)
            logger.info(f"✅ Directory ensured: {dir_path}")
        
        # Check environment variables
        required_env_vars = ["BINANCE_API_KEY", "BINANCE_API_SECRET"]
        missing_env_vars = []
        
        for env_var in required_env_vars:
            if not os.getenv(env_var):
                missing_env_vars.append(env_var)
        
        if missing_env_vars:
            logger.error(f"❌ Missing environment variables: {missing_env_vars}")
            logger.info("💡 Please set them in your .env file")
            return False
        
        logger.info("✅ All prerequisites met!")
        return True
    
    def create_default_env_file(self):
        """Create a default .env file with placeholders"""
        env_content = """# Enhanced Trading Bot Configuration
# ===================================

# Binance API Credentials (REQUIRED)
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here

# Email Notifications (Optional)
SMTP_EMAIL=your_email@gmail.com
SMTP_PASSWORD=your_email_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Telegram Notifications (Optional)  
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Database (Optional - uses SQLite by default)
DATABASE_URL=sqlite:///trading_bot.db

# Monitoring (Optional)
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000

# Advanced Features
OPENAI_API_KEY=your_openai_key_for_ml_features (optional)
"""
        
        with open(".env", "w") as f:
            f.write(env_content)
        
        logger.info("✅ Default .env file created!")
        logger.info("🔧 Please edit .env file with your actual API credentials")
    
    async def setup_mode(self):
        """Setup mode - initial configuration and testing"""
        logger.info("🔧 Running setup mode...")
        
        # Create .env file if it doesn't exist
        if not os.path.exists(".env"):
            self.create_default_env_file()
            logger.info("⚠️ Please configure your .env file and run setup again")
            return
        
        # Check prerequisites
        if not self.check_prerequisites():
            logger.error("❌ Setup failed - prerequisites not met")
            return
        
        # Test Binance connection
        logger.info("🔗 Testing Binance API connection...")
        try:
            from main import BinanceConnector
            connector = BinanceConnector(
                api_key=os.getenv('BINANCE_API_KEY'),
                api_secret=os.getenv('BINANCE_API_SECRET'),
                testnet=True  # Use testnet for setup
            )
            
            # Test basic connectivity
            account_info = await connector.get_account_info()
            if account_info:
                logger.info("✅ Binance API connection successful!")
            else:
                logger.error("❌ Binance API connection failed!")
                return
                
        except Exception as e:
            logger.error(f"❌ Binance API test failed: {e}")
            return
        
        # Run quick backtest
        logger.info("📊 Running quick backtest to validate strategies...")
        try:
            await self.backtest_mode(quick=True)
            logger.info("✅ Setup completed successfully!")
            logger.info("🚀 You can now run: python start_enhanced_bot.py live")
            
        except Exception as e:
            logger.error(f"❌ Setup backtest failed: {e}")
    
    async def backtest_mode(self, quick: bool = False):
        """Backtesting mode - run comprehensive backtests"""
        logger.info("📊 Running backtest mode...")
        
        if not self.check_prerequisites():
            return
        
        try:
            # Load configuration
            config_path = "config/ultra_aggressive.yaml"
            if quick:
                # Quick backtest configuration
                from enhanced_strategy_rules import EnhancedStrategyParams
                
                backtest_config = BacktestConfig(
                    start_date="2024-01-01",
                    end_date="2024-03-01",  # Shorter period for quick test
                    initial_capital=10000.0,
                    symbols=['BTCUSDT', 'ETHUSDT'],  # Just 2 pairs for speed
                    strategy_params=EnhancedStrategyParams()
                )
            else:
                # Full backtesting
                bot = UltraAgressiveTradingBot(config_path)
                return await bot.run_backtests()
            
            # Run the backtest
            results = await run_comprehensive_backtest(backtest_config)
            
            if results:
                logger.info("📊 Backtest Results:")
                logger.info(f"  💰 Total Return: {results.get('total_return', 0):.2%}")
                logger.info(f"  📈 Sharpe Ratio: {results.get('sharpe_ratio', 0):.2f}")
                logger.info(f"  📉 Max Drawdown: {results.get('max_drawdown', 0):.2%}")
                logger.info(f"  🎯 Win Rate: {results.get('win_rate', 0):.2%}")
                logger.info(f"  💎 Profit Factor: {results.get('profit_factor', 0):.2f}")
            else:
                logger.error("❌ Backtest failed to produce results")
                
        except Exception as e:
            logger.error(f"❌ Backtesting failed: {e}")
    
    async def monitor_mode(self):
        """Monitor mode - start monitoring dashboard only"""
        logger.info("📊 Starting monitoring mode...")
        
        try:
            # Start Prometheus monitoring
            monitor = setup_enhanced_monitoring(port=9090)
            await monitor.start()
            
            logger.info("📊 Monitoring dashboard started on http://localhost:9090")
            logger.info("📈 Grafana dashboard available on http://localhost:3000")
            logger.info("👁️ Press Ctrl+C to stop monitoring")
            
            # Keep running until interrupted
            while True:
                await asyncio.sleep(60)
                logger.info("📊 Monitoring active...")
                
        except KeyboardInterrupt:
            logger.info("🛑 Monitoring stopped by user")
        except Exception as e:
            logger.error(f"❌ Monitoring failed: {e}")
    
    async def test_mode(self):
        """Test mode - start bot with testnet"""
        logger.info("🧪 Starting test mode (using Binance testnet)...")
        
        if not self.check_prerequisites():
            return
        
        try:
            # Modify configuration for testnet
            config_path = "config/ultra_aggressive.yaml"
            
            # Override testnet setting
            os.environ['FORCE_TESTNET'] = 'true'
            
            # Initialize bot with testnet
            self.bot = UltraAgressiveTradingBot(config_path)
            
            logger.info("🧪 Test mode bot initialized")
            logger.info("⚠️ All trades will be executed on Binance TESTNET")
            logger.info("💡 No real money will be used")
            
            # Start the bot
            await self.bot.start()
            
        except Exception as e:
            logger.error(f"❌ Test mode failed: {e}")
    
    async def live_mode(self):
        """Live mode - start bot with real trading"""
        logger.info("🚀 Starting LIVE trading mode...")
        logger.warning("⚠️ REAL MONEY TRADING - PROCEED WITH CAUTION!")
        
        if not self.check_prerequisites():
            return
        
        # Final confirmation for live trading
        if not os.getenv('SKIP_CONFIRMATION'):
            print("\n" + "="*60)
            print("⚠️ WARNING: LIVE TRADING MODE")
            print("This will trade with REAL MONEY on your Binance account!")
            print(f"💰 Base Capital: ${3804:.2f}")
            print(f"⚡ Max Risk per Trade: 8%")
            print(f"📊 Max Daily Risk: 15%")
            print("="*60)
            
            confirmation = input("\nType 'LIVE TRADE' to confirm: ")
            if confirmation.strip() != "LIVE TRADE":
                logger.info("❌ Live trading cancelled by user")
                return
        
        try:
            # Initialize bot for live trading
            config_path = "config/ultra_aggressive.yaml"
            self.bot = UltraAgressiveTradingBot(config_path)
            
            logger.info("🚀 Live trading bot initialized")
            logger.info("💰 Trading with REAL money")
            logger.info("📊 Maximum 1000x potential mode activated")
            
            # Start the bot
            await self.bot.start()
            
        except Exception as e:
            logger.error(f"❌ Live trading failed: {e}")
            if self.bot:
                await self.bot.stop()

def main():
    """Main entry point with argument parsing"""
    
    parser = argparse.ArgumentParser(
        description="Enhanced Crypto Trading Bot Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start_enhanced_bot.py setup          # Initial setup and configuration
  python start_enhanced_bot.py backtest       # Run comprehensive backtesting  
  python start_enhanced_bot.py test           # Test with Binance testnet
  python start_enhanced_bot.py live           # Start live trading (REAL MONEY)
  python start_enhanced_bot.py monitor        # Start monitoring dashboard only
        """
    )
    
    parser.add_argument(
        "mode",
        nargs="?",
        default="live",
        choices=["setup", "backtest", "test", "live", "monitor"],
        help="Bot operation mode (default: live)"
    )
    
    parser.add_argument(
        "--config",
        default="config/ultra_aggressive.yaml",
        help="Path to configuration file"
    )
    
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode for backtest (shorter timeframe)"
    )
    
    args = parser.parse_args()
    
    # Create bot manager
    manager = EnhancedBotManager(mode=args.mode)
    
    # Run the appropriate mode
    try:
        if args.mode == "setup":
            asyncio.run(manager.setup_mode())
        elif args.mode == "backtest":
            asyncio.run(manager.backtest_mode(quick=args.quick))
        elif args.mode == "test":
            asyncio.run(manager.test_mode())
        elif args.mode == "live":
            asyncio.run(manager.live_mode())
        elif args.mode == "monitor":
            asyncio.run(manager.monitor_mode())
            
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()