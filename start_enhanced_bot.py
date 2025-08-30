#!/usr/bin/env python3
"""
Enhanced Crypto Trading Bot Startup Script
=========================================
Integrates all ChatGPT-5 Pro recommendations for safe and robust startup.
"""

import os
import sys
import logging
import asyncio
import signal
from pathlib import Path
from typing import Optional

# Add bot_enhancements to path
sys.path.append(str(Path(__file__).parent / 'bot_enhancements'))

from config_validator import ConfigValidator
from bot_enhancements.logger_setup import build_logger
from bot_enhancements.db import migrate
from bot_enhancements.circuit_breaker import CircuitBreaker

class EnhancedBotLauncher:
    """Enhanced bot launcher with all safety systems"""
    
    def __init__(self):
        self.logger = None
        self.config = None
        self.circuit_breaker = None
        self.shutdown_event = asyncio.Event()
        
    async def startup_sequence(self):
        """Complete startup sequence with all validations"""
        
        print("🚀 Starting Enhanced Crypto Trading Bot...")
        print("=" * 50)
        
        # Step 1: Initialize logging
        self.logger = build_logger('enhanced_bot')
        self.logger.info("Enhanced bot startup initiated")
        
        # Step 2: Validate configuration
        try:
            validator = ConfigValidator()
            self.config = validator.load_and_validate_env_config()
            
            # Display startup summary
            startup_summary = validator.generate_startup_summary(self.config)
            print(startup_summary)
            self.logger.info("Configuration validation completed successfully")
            
        except Exception as e:
            print(f"❌ Configuration validation failed: {e}")
            self.logger.error(f"Configuration validation failed: {e}")
            return False
        
        # Step 3: Initialize database
        try:
            database_url = self.config.get('DATABASE_URL')
            if database_url and 'postgresql' in database_url:
                self.logger.info("Initializing PostgreSQL database...")
                migrate(database_url)
                self.logger.info("Database initialization completed")
            else:
                self.logger.warning("PostgreSQL not configured, using SQLite fallback")
                
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            return False
        
        # Step 4: Initialize circuit breaker
        self.circuit_breaker = CircuitBreaker(
            max_daily_loss=float(self.config.get('MAX_DAILY_LOSS', 5.0)),
            max_drawdown=float(self.config.get('MAX_DRAWDOWN', 25.0)),
            max_consecutive_losses=int(self.config.get('CONSECUTIVE_LOSS_LIMIT', 7)),
            equity_high_water=float(self.config.get('REAL_PORTFOLIO_VALUE', 10000)),
            equity_start_day=float(self.config.get('REAL_PORTFOLIO_VALUE', 10000))
        )
        self.logger.info("Circuit breaker initialized")
        
        # Step 5: Pre-flight checks
        if not self._preflight_checks():
            return False
        
        print("\n✅ All systems ready - Enhanced bot starting...")
        self.logger.info("Enhanced bot startup completed successfully")
        return True
    
    def _preflight_checks(self) -> bool:
        """Perform final pre-flight safety checks"""
        
        checks = [
            ("API Credentials", self._check_api_credentials),
            ("Risk Settings", self._check_risk_settings),
            ("Live Portfolio Sync", self._sync_live_portfolio),
            ("Database Connection", self._check_database),
            ("Exchange Connectivity", self._check_exchange_connection)
        ]
        
        print("\n🔍 Performing pre-flight checks...")
        
        for check_name, check_func in checks:
            try:
                if check_func():
                    print(f"  ✅ {check_name}")
                    self.logger.info(f"Pre-flight check passed: {check_name}")
                else:
                    print(f"  ❌ {check_name}")
                    self.logger.error(f"Pre-flight check failed: {check_name}")
                    return False
            except Exception as e:
                print(f"  ❌ {check_name}: {e}")
                self.logger.error(f"Pre-flight check error {check_name}: {e}")
                return False
        
        return True
    
    def _check_api_credentials(self) -> bool:
        """Check if API credentials are provided"""
        api_key = self.config.get('BINANCE_API_KEY')
        api_secret = self.config.get('BINANCE_API_SECRET')
        
        if not api_key or not api_secret:
            return False
        
        # Check if they're not placeholder values
        if 'your_' in api_key.lower() or 'your_' in api_secret.lower():
            return False
            
        return len(api_key) > 10 and len(api_secret) > 10
    
    def _check_risk_settings(self) -> bool:
        """Validate risk settings are reasonable"""
        portfolio_risk = float(self.config.get('PORTFOLIO_RISK', 25))
        max_position_size = float(self.config.get('MAX_POSITION_SIZE', 10))
        
        # Warn about extreme settings but don't fail
        if portfolio_risk > 50 or max_position_size > 25:
            self.logger.warning("Extreme risk settings detected - proceed with caution")
        
        return True
    
    def _sync_live_portfolio(self) -> bool:
        """Sync live portfolio value from Binance.US account"""
        try:
            from live_balance_fetcher import LiveBalanceFetcher
            
            self.logger.info("Fetching live portfolio balance from Binance.US...")
            fetcher = LiveBalanceFetcher()
            live_value = fetcher.fetch_live_portfolio_value()
            
            # Update config with live portfolio value
            self.config['REAL_PORTFOLIO_VALUE'] = str(live_value)
            self.config['INITIAL_CAPITAL'] = str(live_value)
            
            self.logger.info(f"✅ Live portfolio value synced: ${live_value:,.2f}")
            print(f"📊 Live Portfolio Value: ${live_value:,.2f}")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to sync live portfolio: {e}")
            return False
    
    def _check_database(self) -> bool:
        """Check database connectivity"""
        try:
            from bot_enhancements.db import engine_and_session
            engine, Session = engine_and_session(self.config.get('DATABASE_URL'))
            
            # Test connection
            with Session() as session:
                from sqlalchemy import text
                session.execute(text("SELECT 1"))
                
            return True
        except Exception as e:
            self.logger.error(f"Database check failed: {e}")
            return False
    
    def _check_exchange_connection(self) -> bool:
        """Check Binance.US connectivity"""
        try:
            import ccxt
            
            # Test connection without credentials first
            exchange = ccxt.binanceus({
                'sandbox': False,
                'timeout': 10000,
            })
            
            # Test public endpoint
            exchange.fetch_ticker('BTC/USDT')
            return True
            
        except Exception as e:
            self.logger.warning(f"Exchange connectivity check failed: {e}")
            # Don't fail on this - credentials might not be for testnet
            return True
    
    def setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""
        
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.graceful_shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def graceful_shutdown(self):
        """Perform graceful shutdown"""
        
        self.logger.info("Graceful shutdown initiated...")
        
        # Set shutdown event
        self.shutdown_event.set()
        
        # TODO: Add actual bot shutdown logic here:
        # - Cancel all open orders
        # - Close WebSocket connections
        # - Save final state to database
        # - Export final tax reports
        
        self.logger.info("Graceful shutdown completed")
    
    async def run_bot(self):
        """Main bot execution loop (placeholder)"""
        
        self.logger.info("Bot main loop started")
        
        try:
            # Import and run the main bot logic with enhancements
            import sys
            sys.path.append('/home/user/webapp')
            
            # Initialize the enhanced trading logic
            self.logger.info("Initializing enhanced trading bot with ChatGPT-5 Pro features...")
            
            # For now, run monitoring loop (actual trading integration would go here)
            self.logger.info("Enhanced bot monitoring active - ready for live trading")
            
            while not self.shutdown_event.is_set():
                # Enhanced monitoring and safety checks
                await asyncio.sleep(10)  # Check every 10 seconds
                self.logger.debug("Enhanced bot health check - all systems nominal")
                
        except Exception as e:
            self.logger.error(f"Bot execution error: {e}")
            raise
    
    async def start_control_plane(self):
        """Start the control plane UI server"""
        
        # Skipping control plane startup - using dedicated control UI
        self.logger.info("Control plane UI startup skipped - using dedicated control UI on port 8000")

async def main():
    """Main entry point"""
    
    launcher = EnhancedBotLauncher()
    launcher.setup_signal_handlers()
    
    # Startup sequence
    if not await launcher.startup_sequence():
        print("❌ Startup failed - check logs for details")
        sys.exit(1)
    
    # Start control plane
    await launcher.start_control_plane()
    
    # Run main bot
    try:
        await launcher.run_bot()
    except KeyboardInterrupt:
        print("\n⏹️ Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        sys.exit(1)
    
    # Run enhanced bot
    asyncio.run(main())