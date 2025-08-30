#!/usr/bin/env python3
"""
Ultra-Aggressive Enhanced Crypto Trading Bot
===========================================

Maximum 1000x potential trading system with institutional-grade features.
This is the main entry point that integrates all enhanced components.

Features:
✅ Enhanced strategy rules with ML-powered regime detection
✅ Dynamic risk management with performance-based scaling  
✅ Advanced execution engine with TWAP and iceberg orders
✅ Prometheus monitoring with real-time PnL alerts
✅ Comprehensive tax tracking with fee-adjusted calculations
✅ Advanced backtesting framework with Monte Carlo simulation
✅ All 183 Binance.US trading pairs for maximum opportunities
"""

import asyncio
import signal
import sys
import os
import logging
import json
import yaml
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict

# Enhanced Trading Bot Components
from enhanced_strategy_rules import (
    generate_enhanced_signals, 
    EnhancedStrategyParams, 
    EnhancedRegimeConfig,
    detect_market_regime_ml
)
from enhanced_risk_manager import (
    EnhancedRiskManager, 
    DynamicRiskConfig,
    RiskMetrics
)
from enhanced_execution_engine import (
    EnhancedExecutionEngine, 
    EnhancedOrder, 
    OrderType, 
    TWAPConfig, 
    IcebergConfig
)
from enhanced_monitoring import (
    EnhancedMonitor, 
    setup_enhanced_monitoring,
    PrometheusMetrics
)
from enhanced_tax_integration import (
    TaxCalculationEngine, 
    CostBasisMethod,
    TaxReport
)
from enhanced_backtesting import (
    BacktestConfig, 
    run_comprehensive_backtest,
    MonteCarloConfig
)

# Original components
from main import BinanceConnector  # Your existing connector
from notifier import notify_email, notify_telegram

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/ultra_aggressive_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class UltraAgressiveTradingBot:
    """
    Ultra-aggressive trading bot with all enhanced features integrated.
    Designed for maximum 1000x potential with institutional risk management.
    """
    
    def __init__(self, config_path: str = "config/ultra_aggressive.yaml"):
        """Initialize the enhanced trading bot with all components"""
        self.config_path = config_path
        self.config = self.load_config()
        self.running = False
        
        # Initialize core components
        self.binance_connector = BinanceConnector(
            api_key=os.getenv('BINANCE_API_KEY'),
            api_secret=os.getenv('BINANCE_API_SECRET'),
            testnet=self.config.get('binance', {}).get('testnet', False)
        )
        
        # Initialize enhanced components
        self.setup_enhanced_components()
        
        logger.info("🚀 Ultra-Aggressive Enhanced Trading Bot initialized!")
        logger.info(f"💰 Base Capital: ${self.config['trading']['base_capital']:,.2f}")
        logger.info(f"📊 Max Concurrent Positions: {self.config['trading']['max_concurrent_positions']}")
        logger.info(f"⚡ Risk Range: {self.config['trading']['risk_management']['min_risk_per_trade']:.1%} - {self.config['trading']['risk_management']['max_risk_per_trade']:.1%}")
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as file:
                config = yaml.safe_load(file)
                logger.info(f"✅ Configuration loaded from {self.config_path}")
                return config
        except FileNotFoundError:
            logger.error(f"❌ Configuration file not found: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"❌ Error parsing YAML configuration: {e}")
            raise
    
    def setup_enhanced_components(self):
        """Initialize all enhanced trading components"""
        
        # 1. Enhanced Risk Manager
        risk_config = DynamicRiskConfig(
            base_risk_per_trade=self.config['trading']['risk_management']['base_risk_per_trade'],
            max_risk_per_trade=self.config['trading']['risk_management']['max_risk_per_trade'],
            min_risk_per_trade=self.config['trading']['risk_management']['min_risk_per_trade'],
            max_daily_risk=self.config['trading']['risk_management']['max_daily_risk'],
            max_correlation=self.config['trading']['risk_management']['max_correlation'],
        )
        
        self.risk_manager = EnhancedRiskManager(
            config=risk_config,
            initial_capital=self.config['trading']['base_capital']
        )
        
        # 2. Enhanced Execution Engine
        twap_config = TWAPConfig(
            time_horizon_minutes=self.config['execution']['twap']['time_horizon'] // 60,
            slice_count=self.config['execution']['twap']['slice_count']
        )
        
        iceberg_config = IcebergConfig(
            visible_ratio=self.config['execution']['iceberg']['visible_ratio']
        )
        
        self.execution_engine = EnhancedExecutionEngine(
            binance_connector=self.binance_connector,
            twap_config=twap_config,
            iceberg_config=iceberg_config
        )
        
        # 3. Enhanced Strategy Parameters
        self.strategy_params = EnhancedStrategyParams(
            momentum_weight=self.config['strategies']['momentum']['weight'],
            mean_reversion_weight=self.config['strategies']['mean_reversion']['weight'],
            breakout_weight=self.config['strategies']['breakout']['weight'],
            volatility_filter=self.config['strategies']['momentum']['volatility_filter'],
            macd_confirmation=self.config['strategies']['mean_reversion']['macd_confirmation'],
            short_selling=self.config['strategies']['breakout']['short_selling']
        )
        
        # 4. Enhanced Monitoring
        if self.config['monitoring']['prometheus']['enabled']:
            self.monitor = setup_enhanced_monitoring(
                port=self.config['monitoring']['prometheus']['port']
            )
        
        # 5. Tax Tracking Engine
        if self.config['tax_tracking']['enabled']:
            cost_basis_method = CostBasisMethod[self.config['tax_tracking']['method']]
            self.tax_engine = TaxCalculationEngine(
                cost_basis_method=cost_basis_method,
                include_fees=self.config['tax_tracking']['include_fees']
            )
        
        # 6. Load Trading Pairs
        self.trading_pairs = self.load_trading_pairs()
        
        logger.info("✅ All enhanced components initialized successfully!")
    
    def load_trading_pairs(self) -> List[str]:
        """Load all available trading pairs for maximum market coverage"""
        try:
            pairs_file = self.config['trading']['trading_pairs_file']
            with open(pairs_file, 'r') as f:
                pairs_data = json.load(f)
                
            if self.config['trading']['use_all_pairs']:
                pairs = [pair['symbol'] for pair in pairs_data]
                logger.info(f"📈 Loaded {len(pairs)} trading pairs for maximum market coverage")
                return pairs
            else:
                # Use default pairs if not using all pairs
                return ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT']
                
        except FileNotFoundError:
            logger.warning(f"⚠️ Trading pairs file not found, using default pairs")
            return ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT']
    
    async def get_market_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch market data for a trading pair"""
        try:
            # Get historical data (last 100 candles for analysis)
            klines = await self.binance_connector.get_historical_klines(
                symbol=symbol,
                interval='1h',
                limit=100
            )
            
            if not klines:
                return None
                
            # Convert to DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 
                'volume', 'close_time', 'quote_volume', 'trades',
                'taker_buy_base', 'taker_buy_quote', 'ignore'
            ])
            
            # Convert to numeric types
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            df[numeric_columns] = df[numeric_columns].astype(float)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Error fetching market data for {symbol}: {e}")
            return None
    
    async def analyze_market_signals(self, symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate trading signals using enhanced strategy rules"""
        try:
            # Detect current market regime
            regime = detect_market_regime_ml(df)
            
            # Generate enhanced signals
            signals = generate_enhanced_signals(
                df=df,
                params=self.strategy_params,
                regime=regime
            )
            
            return {
                'symbol': symbol,
                'regime': regime,
                'signals': signals,
                'current_price': df['close'].iloc[-1],
                'volume': df['volume'].iloc[-1],
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"❌ Error analyzing signals for {symbol}: {e}")
            return None
    
    async def execute_trade_if_needed(self, analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute trade based on analysis and risk management"""
        try:
            symbol = analysis['symbol']
            signals = analysis['signals']
            current_price = analysis['current_price']
            
            # Check if we have a trading signal
            if not signals.get('should_trade', False):
                return None
            
            # Get risk assessment
            risk_assessment = self.risk_manager.assess_trade_risk(
                symbol=symbol,
                signal_strength=signals.get('signal_strength', 0.5),
                current_price=current_price,
                regime=analysis['regime']
            )
            
            if not risk_assessment.approved:
                logger.info(f"🚫 Trade rejected for {symbol}: {risk_assessment.rejection_reason}")
                return None
            
            # Create enhanced order
            order_type = OrderType.MARKET  # Start with market orders for speed
            side = signals['side']  # 'buy' or 'sell'
            quantity = risk_assessment.position_size
            
            enhanced_order = EnhancedOrder(
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=current_price if order_type == OrderType.LIMIT else None,
                stop_loss=signals.get('stop_loss'),
                take_profit=signals.get('take_profit')
            )
            
            # Execute the order
            execution_result = await self.execution_engine.execute_order(enhanced_order)
            
            if execution_result.success:
                # Update risk manager
                self.risk_manager.update_position(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=execution_result.fill_price,
                    fees=execution_result.fees
                )
                
                # Update tax tracking
                if hasattr(self, 'tax_engine'):
                    self.tax_engine.record_trade(
                        symbol=symbol,
                        side=side,
                        quantity=quantity,
                        price=execution_result.fill_price,
                        fees=execution_result.fees,
                        timestamp=datetime.now()
                    )
                
                # Update monitoring
                if hasattr(self, 'monitor'):
                    self.monitor.record_trade(execution_result)
                
                # Send notification
                await self.send_trade_notification(enhanced_order, execution_result)
                
                logger.info(f"✅ Trade executed for {symbol}: {side} {quantity} at ${execution_result.fill_price:.6f}")
                
                return {
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                    'fill_price': execution_result.fill_price,
                    'fees': execution_result.fees,
                    'order_id': execution_result.order_id
                }
            else:
                logger.error(f"❌ Trade execution failed for {symbol}: {execution_result.error}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error executing trade for {analysis.get('symbol', 'Unknown')}: {e}")
            return None
    
    async def send_trade_notification(self, order: EnhancedOrder, result):
        """Send notifications about executed trades"""
        try:
            message = f"""
🚀 ULTRA-AGGRESSIVE BOT TRADE EXECUTED

Symbol: {order.symbol}
Action: {order.side.upper()}
Quantity: {order.quantity}
Fill Price: ${result.fill_price:.6f}
Fees: ${result.fees:.6f}
Order ID: {result.order_id}

💰 Current Portfolio Value: ${self.risk_manager.get_portfolio_value():,.2f}
📊 Daily PnL: {self.risk_manager.get_daily_pnl():.2%}
            """
            
            # Email notification
            if self.config['monitoring']['alerts']['email']['enabled']:
                await notify_email(
                    subject="Ultra-Aggressive Bot: Trade Executed",
                    message=message
                )
            
            # Telegram notification
            if self.config['monitoring']['alerts']['telegram']['enabled']:
                await notify_telegram(message)
                
        except Exception as e:
            logger.error(f"❌ Error sending trade notification: {e}")
    
    async def check_portfolio_alerts(self):
        """Check for portfolio-level alerts and notifications"""
        try:
            portfolio_metrics = self.risk_manager.get_portfolio_metrics()
            daily_pnl = portfolio_metrics.daily_pnl_percent
            
            # Check PnL alert thresholds
            warning_threshold = self.config['monitoring']['alerts']['pnl_thresholds']['warning']
            critical_threshold = self.config['monitoring']['alerts']['pnl_thresholds']['critical']
            
            if daily_pnl <= critical_threshold:
                await self.send_alert(
                    level="CRITICAL",
                    message=f"🚨 CRITICAL: Daily PnL at {daily_pnl:.2%} (Below {critical_threshold:.2%})"
                )
            elif daily_pnl <= warning_threshold:
                await self.send_alert(
                    level="WARNING", 
                    message=f"⚠️ WARNING: Daily PnL at {daily_pnl:.2%} (Below {warning_threshold:.2%})"
                )
            
            # Check performance degradation
            if portfolio_metrics.win_rate < self.config['monitoring']['alerts']['performance_alerts']['win_rate_threshold']:
                await self.send_alert(
                    level="WARNING",
                    message=f"📉 Performance Alert: Win rate dropped to {portfolio_metrics.win_rate:.2%}"
                )
                
        except Exception as e:
            logger.error(f"❌ Error checking portfolio alerts: {e}")
    
    async def send_alert(self, level: str, message: str):
        """Send alert notifications"""
        try:
            alert_message = f"🤖 Ultra-Aggressive Bot Alert [{level}]\n\n{message}"
            
            if self.config['monitoring']['alerts']['email']['enabled']:
                await notify_email(
                    subject=f"Bot Alert [{level}]",
                    message=alert_message
                )
                
            if self.config['monitoring']['alerts']['telegram']['enabled']:
                await notify_telegram(alert_message)
                
            logger.warning(f"Alert sent [{level}]: {message}")
            
        except Exception as e:
            logger.error(f"❌ Error sending alert: {e}")
    
    async def trading_loop(self):
        """Main trading loop with enhanced features"""
        logger.info("🔄 Starting ultra-aggressive trading loop...")
        
        while self.running:
            try:
                loop_start_time = datetime.now()
                executed_trades = []
                
                # Analyze all trading pairs in parallel for speed
                analysis_tasks = []
                for symbol in self.trading_pairs[:20]:  # Start with first 20 pairs, expand gradually
                    analysis_tasks.append(self.analyze_symbol(symbol))
                
                # Wait for all analysis to complete
                analysis_results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
                
                # Process successful analyses
                for result in analysis_results:
                    if isinstance(result, dict) and result:
                        trade_result = await self.execute_trade_if_needed(result)
                        if trade_result:
                            executed_trades.append(trade_result)
                
                # Portfolio management
                await self.check_portfolio_alerts()
                
                # Log loop performance
                loop_duration = (datetime.now() - loop_start_time).total_seconds()
                logger.info(f"🔄 Trading loop completed in {loop_duration:.2f}s, {len(executed_trades)} trades executed")
                
                # Update monitoring metrics
                if hasattr(self, 'monitor'):
                    self.monitor.update_loop_metrics(
                        duration=loop_duration,
                        pairs_analyzed=len([r for r in analysis_results if not isinstance(r, Exception)]),
                        trades_executed=len(executed_trades)
                    )
                
                # Wait before next loop (respect rate limits)
                await asyncio.sleep(30)  # 30-second intervals for aggressive trading
                
            except Exception as e:
                logger.error(f"❌ Error in trading loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def analyze_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Analyze a single symbol for trading opportunities"""
        try:
            # Get market data
            df = await self.get_market_data(symbol)
            if df is None or len(df) < 50:  # Need enough data for analysis
                return None
            
            # Generate analysis
            analysis = await self.analyze_market_signals(symbol, df)
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error analyzing {symbol}: {e}")
            return None
    
    async def run_backtests(self):
        """Run comprehensive backtesting before live trading"""
        logger.info("📊 Running comprehensive backtesting analysis...")
        
        try:
            backtest_config = BacktestConfig(
                start_date=self.config['backtesting']['start_date'],
                end_date=self.config['backtesting']['end_date'],
                initial_capital=self.config['backtesting']['initial_capital'],
                symbols=self.trading_pairs[:10],  # Test with first 10 pairs
                strategy_params=self.strategy_params
            )
            
            # Run backtesting
            results = await run_comprehensive_backtest(backtest_config)
            
            if results:
                logger.info("📊 Backtesting Results:")
                logger.info(f"  💰 Total Return: {results.get('total_return', 0):.2%}")
                logger.info(f"  📈 Sharpe Ratio: {results.get('sharpe_ratio', 0):.2f}")
                logger.info(f"  📉 Max Drawdown: {results.get('max_drawdown', 0):.2%}")
                logger.info(f"  🎯 Win Rate: {results.get('win_rate', 0):.2%}")
                
                return True
            else:
                logger.warning("⚠️ Backtesting failed, proceeding with caution")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error running backtests: {e}")
            return False
    
    async def start(self):
        """Start the ultra-aggressive trading bot"""
        logger.info("🚀 Starting Ultra-Aggressive Enhanced Trading Bot...")
        
        # Run backtests first (optional but recommended)
        if self.config['backtesting']['enabled']:
            backtest_success = await self.run_backtests()
            if not backtest_success:
                logger.warning("⚠️ Backtesting issues detected, but continuing...")
        
        # Initialize risk manager with current portfolio state
        await self.risk_manager.initialize_portfolio(self.binance_connector)
        
        # Set running flag
        self.running = True
        
        # Start monitoring if enabled
        if hasattr(self, 'monitor'):
            await self.monitor.start()
        
        # Send startup notification
        await self.send_alert(
            level="INFO",
            message=f"🚀 Ultra-Aggressive Bot Started!\n💰 Capital: ${self.config['trading']['base_capital']:,.2f}\n📊 Pairs: {len(self.trading_pairs)}"
        )
        
        # Start main trading loop
        await self.trading_loop()
    
    async def stop(self):
        """Stop the trading bot gracefully"""
        logger.info("🛑 Stopping Ultra-Aggressive Enhanced Trading Bot...")
        
        self.running = False
        
        # Generate final tax report if enabled
        if hasattr(self, 'tax_engine') and self.config['tax_tracking']['auto_export']:
            try:
                tax_report = self.tax_engine.generate_tax_report()
                export_path = f"tax_reports/tax_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                os.makedirs(os.path.dirname(export_path), exist_ok=True)
                tax_report.to_csv(export_path)
                logger.info(f"📋 Tax report exported to {export_path}")
            except Exception as e:
                logger.error(f"❌ Error generating tax report: {e}")
        
        # Stop monitoring
        if hasattr(self, 'monitor'):
            await self.monitor.stop()
        
        # Send shutdown notification
        portfolio_value = self.risk_manager.get_portfolio_value()
        daily_pnl = self.risk_manager.get_daily_pnl()
        
        await self.send_alert(
            level="INFO",
            message=f"🛑 Bot Stopped\n💰 Final Portfolio: ${portfolio_value:,.2f}\n📊 Daily PnL: {daily_pnl:.2%}"
        )
        
        logger.info("✅ Ultra-Aggressive Enhanced Trading Bot stopped successfully!")

def setup_signal_handlers(bot: UltraAgressiveTradingBot):
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        logger.info(f"📶 Received signal {signum}, shutting down gracefully...")
        asyncio.create_task(bot.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

async def main():
    """Main entry point for the ultra-aggressive enhanced trading bot"""
    
    # Ensure required directories exist
    os.makedirs('logs', exist_ok=True)
    os.makedirs('config', exist_ok=True)
    os.makedirs('tax_reports', exist_ok=True)
    
    # Initialize bot
    bot = UltraAgressiveTradingBot()
    
    # Setup signal handlers
    setup_signal_handlers(bot)
    
    try:
        # Start the bot
        await bot.start()
        
    except KeyboardInterrupt:
        logger.info("👋 Keyboard interrupt received")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
    finally:
        await bot.stop()

if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())