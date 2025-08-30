"""
Enhanced Trading Bot Integration Guide
====================================

This guide shows how to integrate all the enhanced features into your 
existing aggressive crypto trading bot for maximum 1000x potential.

Features Integrated:
✅ Enhanced strategy rules with volatility breakout, MACD confirmation, short selling
✅ Dynamic risk management with equity-based scaling
✅ Advanced execution engine with TWAP/Iceberg orders
✅ Prometheus monitoring with PNL alerts
✅ Enhanced tax tracking with fee-adjusted R-multiples
✅ Comprehensive backtesting framework
✅ ML-powered regime detection
✅ Chandelier exits and advanced trailing stops
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Import enhanced modules
from enhanced_strategy_rules import (
    generate_enhanced_signals, EnhancedStrategyParams, EnhancedRegimeConfig
)
from enhanced_risk_manager import EnhancedRiskManager, DynamicRiskConfig
from enhanced_execution_engine import (
    EnhancedExecutionEngine, EnhancedOrder, OrderType, TWAPConfig, IcebergConfig
)
from enhanced_monitoring import EnhancedMonitor, setup_enhanced_monitoring
from enhanced_tax_integration import TaxCalculationEngine, CostBasisMethod
from enhanced_backtesting import BacktestConfig, run_comprehensive_backtest

# Your existing imports
from main import BinanceConnector  # Your existing connector
from notifier import notify_email, notify_telegram

logger = logging.getLogger(__name__)

class UltraAggresiveTradingBot:
    """
    Ultra-aggressive trading bot with all enhanced features
    Designed for maximum 1000x potential with institutional-grade risk management
    """
    
    def __init__(self, config_path: str = "config/ultra_aggressive.yaml"):
        self.config_path = config_path
        
        # Initialize core components
        self._initialize_components()
        
        logger.info("🚀 Ultra-Aggressive Trading Bot initialized with all enhanced features!")
    
    def _initialize_components(self):
        """Initialize all enhanced components"""
        
        # 1. Enhanced Strategy Configuration
        self.strategy_params = EnhancedStrategyParams(
            # Enhanced parameters for maximum aggressiveness
            atr_period=14,
            stop_atr_mult=2.0,  # Tighter stops for more aggressive entries
            trail_atr_mult=1.5,  # Faster trailing
            partial_tp_r=1.5,
            tp2_r=4.0,  # Higher profit targets
            
            # New enhanced features
            use_macd_confirmation=True,
            use_volatility_filter=True,
            volatility_threshold=1.2,  # Lower threshold = more trades
            enable_short_selling=True,
            short_rsi_threshold=70,
            
            # Execution optimizations
            use_twap_for_large_orders=True,
            large_order_threshold=0.05,  # 5% of daily volume
            twap_duration_minutes=10,  # Faster TWAP execution
            
            # Advanced features
            use_volatility_position_sizing=True,
            volatility_scaling_factor=1.5,
            correlation_threshold=0.65  # Slightly relaxed for more opportunities
        )
        
        # 2. Enhanced Regime Detection
        self.regime_config = EnhancedRegimeConfig(
            adx_trend_threshold=20.0,  # Lower threshold = more trend detection
            crash_threshold=-0.05,  # More sensitive crash detection
            use_ml_classification=True,  # Enable ML regime detection
            ml_lookback=150,
            volatility_threshold=1.2,
            correlation_threshold=0.65
        )
        
        # 3. Dynamic Risk Management
        self.dynamic_risk_config = DynamicRiskConfig(
            base_risk_per_trade=0.03,  # 3% base risk (aggressive)
            min_risk_per_trade=0.01,   # 1% minimum
            max_risk_per_trade=0.08,   # 8% maximum (ultra-aggressive)
            
            # Performance scaling thresholds
            win_rate_threshold_high=65.0,   # Scale up at 65% win rate
            win_rate_threshold_low=45.0,    # Scale down at 45% win rate
            profit_factor_threshold_high=1.8,  # Scale up at 1.8 PF
            profit_factor_threshold_low=1.1,   # Scale down at 1.1 PF
            
            # Consecutive trade handling
            max_consecutive_losses_before_reduction=2,  # Faster reduction
            consecutive_wins_before_increase=3,         # Faster increase
            
            # Scaling factors
            performance_scaling_factor=0.6,  # More aggressive scaling
            volatility_scaling_enabled=True,
            correlation_scaling_enabled=True
        )
        
        # 4. Enhanced Risk Manager
        self.risk_manager = EnhancedRiskManager(
            max_portfolio_heat=0.15,    # 15% max heat (aggressive)
            max_daily_loss=0.08,        # 8% daily loss limit
            max_drawdown=0.20,          # 20% max drawdown
            max_concurrent=12,          # More concurrent positions
            
            # Enhanced parameters
            correlation_gate=True,
            corr_threshold=0.65,
            volatility_adjustment=True,
            dynamic_risk_scaling=True,
            
            # Fee rates
            maker_fee_rate=0.0008,      # 0.08% maker fee
            taker_fee_rate=0.0012,      # 0.12% taker fee
            
            # Dynamic configuration
            dynamic_config=self.dynamic_risk_config,
            
            # Alerts
            daily_pnl_alert_threshold=-0.06  # Alert at -6% daily loss
        )
        
        # 5. Enhanced Monitoring System
        self.monitor = setup_enhanced_monitoring(prometheus_port=8002)
        
        # Setup PnL alert callback
        def pnl_alert_handler(level: str, message: str):
            """Handle PnL alerts"""
            if level in ["CRITICAL", "WARNING"]:
                try:
                    notify_email(f"Trading Bot Alert [{level}]", message)
                    notify_telegram(f"🤖 *Ultra-Aggressive Bot Alert*\n\n{message}")
                except Exception as e:
                    logger.error(f"Alert notification failed: {e}")
        
        self.risk_manager.set_pnl_alert_callback(pnl_alert_handler)
        self.monitor.add_alert_callback(pnl_alert_handler)
        
        # 6. Tax Integration System
        self.tax_engine = TaxCalculationEngine(
            db_path="ultra_aggressive_tax.db",
            cost_basis_method=CostBasisMethod.FIFO
        )
        
        # 7. Enhanced Execution Engine (will be initialized with market data)
        self.execution_engine: Optional[EnhancedExecutionEngine] = None
        
        # 8. Position tracking
        self.active_positions: Dict = {}
        
        logger.info("✅ All enhanced components initialized")
    
    async def initialize_execution_engine(self, market_data_provider, exchange_connector):
        """Initialize execution engine with market data and exchange connections"""
        
        self.execution_engine = EnhancedExecutionEngine(
            market_data=market_data_provider,
            exchange=exchange_connector
        )
        
        logger.info("✅ Enhanced execution engine initialized")
    
    async def run_enhanced_trading_cycle(self, symbols: List[str], market_data: Dict):
        """
        Run one complete enhanced trading cycle
        
        Args:
            symbols: List of trading symbols (all 183 pairs)
            market_data: Dictionary of OHLCV data for each symbol
        """
        
        try:
            # Get current equity and start risk management cycle
            current_equity = await self._get_current_equity()
            current_time = datetime.now()
            
            self.risk_manager.on_bar_start(current_time, current_equity)
            
            # Check if trading is enabled
            can_trade, reason = self.risk_manager.can_trade()
            if not can_trade:
                logger.warning(f"Trading disabled: {reason}")
                
                # Send alert for trading disabled
                self.monitor.record_signal_generation("SYSTEM", "risk_management", "trading_disabled")
                return
            
            # Calculate dynamic risk per trade
            market_volatility = await self._calculate_market_volatility(market_data)
            current_risk_per_trade = self.risk_manager.calculate_dynamic_risk_per_trade(
                current_equity, market_volatility
            )
            
            logger.info(f"📊 Current dynamic risk per trade: {current_risk_per_trade:.1%}")
            
            # Process each symbol for new signals
            new_signals = []
            
            for symbol in symbols:
                if symbol in self.active_positions:
                    continue  # Skip symbols with active positions
                
                # Get market data for symbol
                df = market_data.get(symbol)
                if df is None or len(df) < 200:
                    continue
                
                # Generate enhanced signals
                try:
                    signals = generate_enhanced_signals(
                        df=df,
                        symbol=symbol,
                        enabled=('enhanced_momentum', 'enhanced_mean_reversion', 'enhanced_breakout'),
                        params=self.strategy_params,
                        regime_cfg=self.regime_config
                    )
                    
                    if signals:
                        # Take the latest signal
                        latest_signal = signals[-1]
                        
                        # Record signal generation
                        self.monitor.record_signal_generation(
                            symbol, latest_signal.entry.tag, latest_signal.entry.side
                        )
                        
                        new_signals.append(latest_signal)
                        
                except Exception as e:
                    logger.error(f"Signal generation failed for {symbol}: {e}")
            
            logger.info(f"🎯 Generated {len(new_signals)} new signals")
            
            # Process new signals with enhanced risk management
            for signal in new_signals:
                await self._process_enhanced_signal(signal, current_equity, current_risk_per_trade)
            
            # Manage existing positions with enhanced exits
            await self._manage_enhanced_positions(market_data)
            
            # Update monitoring metrics
            await self._update_monitoring_metrics(current_equity)
            
            logger.info("✅ Enhanced trading cycle completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Enhanced trading cycle failed: {e}")
            
            # Send critical alert
            if hasattr(self, 'monitor'):
                self.monitor._send_alert("CRITICAL", f"Trading cycle failure: {str(e)}")
    
    async def _process_enhanced_signal(self, signal, current_equity: float, risk_per_trade: float):
        """Process signal with enhanced risk management and execution"""
        
        try:
            symbol = signal.symbol
            entry_price = signal.entry.price
            stop_price = signal.exit_plan.stop_price
            
            # Calculate correlation with existing positions
            correlation = await self._calculate_symbol_correlation(symbol)
            
            # Get current ATR for volatility adjustment
            atr_value = await self._get_current_atr(symbol)
            
            # Enhanced position assessment
            assessment = self.risk_manager.assess_enhanced_position(
                symbol=symbol,
                entry_price=entry_price,
                stop_price=stop_price,
                equity=current_equity,
                risk_per_trade_fraction=risk_per_trade,
                avg_pairwise_corr=correlation,
                atr=atr_value,
                side=signal.entry.side,
                is_maker_order=True  # Prefer maker orders for better fees
            )
            
            if not assessment.accept:
                logger.info(f"❌ Signal rejected for {symbol}: {assessment.reason}")
                return
            
            # Create enhanced order
            order_size = assessment.max_size_units
            
            # Determine optimal execution method
            if self.execution_engine:
                optimal_order_type = self.execution_engine.determine_optimal_execution(
                    symbol, order_size
                )
            else:
                optimal_order_type = OrderType.MARKET  # Fallback
            
            enhanced_order = EnhancedOrder(
                order_id=f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                symbol=symbol,
                side=signal.entry.side,
                size=order_size,
                order_type=optimal_order_type,
                target_price=entry_price
            )
            
            # Add execution configs for advanced order types
            if optimal_order_type == OrderType.TWAP:
                enhanced_order.twap_config = TWAPConfig(
                    duration_minutes=self.strategy_params.twap_duration_minutes,
                    slice_interval_seconds=30,
                    participation_rate=0.12  # 12% participation for aggressive execution
                )
            elif optimal_order_type == OrderType.ICEBERG:
                enhanced_order.iceberg_config = IcebergConfig(
                    visible_size=0.15,  # 15% visible size
                    refresh_interval=3   # 3-second refresh for aggressive execution
                )
            
            # Execute order using enhanced execution engine
            if self.execution_engine:
                execution_result = await self.execution_engine.execute_order(enhanced_order)
                
                if execution_result.status.value in ['filled', 'partially_filled']:
                    # Register successful entry with enhanced risk manager
                    self.risk_manager.register_enhanced_entry(
                        symbol=symbol,
                        entry_price=execution_result.metrics.average_fill_price or entry_price,
                        stop_price=stop_price,
                        size_units=execution_result.filled_size,
                        opened_at=datetime.now(),
                        tag=signal.entry.tag,
                        atr=atr_value,
                        correlation=correlation,
                        side=signal.entry.side,
                        actual_entry_fees=execution_result.metrics.total_fees
                    )
                    
                    # Record with tax engine
                    self.tax_engine.record_acquisition(
                        symbol=symbol,
                        quantity=execution_result.filled_size,
                        price=execution_result.metrics.average_fill_price or entry_price,
                        timestamp=datetime.now(),
                        fees=execution_result.metrics.total_fees,
                        transaction_id=enhanced_order.order_id
                    )
                    
                    # Track position
                    self.active_positions[symbol] = {
                        'signal': signal,
                        'execution_result': execution_result,
                        'entry_time': datetime.now()
                    }
                    
                    # Record successful execution
                    self.monitor.record_signal_generation(
                        symbol, signal.entry.tag, signal.entry.side, executed=True
                    )
                    
                    logger.info(f"✅ Position opened: {symbol} {signal.entry.side} "
                               f"{execution_result.filled_size:.6f} @ "
                               f"{execution_result.metrics.average_fill_price:.4f}")
                
            else:
                logger.warning("⚠️ Execution engine not initialized - using basic order execution")
                # Fallback to basic execution (your existing logic)
                # ... implement basic order execution here
            
        except Exception as e:
            logger.error(f"❌ Failed to process signal for {signal.symbol}: {e}")
    
    async def _manage_enhanced_positions(self, market_data: Dict):
        """Manage existing positions with enhanced exit logic"""
        
        positions_to_close = []
        
        for symbol, position_info in self.active_positions.items():
            try:
                signal = position_info['signal']
                current_price = await self._get_current_price(symbol)
                
                # Enhanced exit logic
                should_exit, exit_reason = await self._check_enhanced_exit_conditions(
                    symbol, signal, current_price, position_info
                )
                
                if should_exit:
                    # Execute enhanced exit
                    await self._execute_enhanced_exit(symbol, position_info, current_price, exit_reason)
                    positions_to_close.append(symbol)
                
            except Exception as e:
                logger.error(f"❌ Position management failed for {symbol}: {e}")
        
        # Clean up closed positions
        for symbol in positions_to_close:
            if symbol in self.active_positions:
                del self.active_positions[symbol]
    
    async def _check_enhanced_exit_conditions(self, symbol: str, signal, current_price: float, position_info: Dict) -> tuple:
        """Check enhanced exit conditions including chandelier exits"""
        
        # Get enhanced exit plan
        exit_plan = signal.exit_plan
        
        # Basic stop loss
        if signal.entry.side == "buy":
            if current_price <= exit_plan.stop_price:
                return True, "stop_loss"
        else:  # short
            if current_price >= exit_plan.stop_price:
                return True, "stop_loss"
        
        # Take profit levels
        if exit_plan.take_profit_prices:
            tp1_price = exit_plan.take_profit_prices[0]
            
            if signal.entry.side == "buy":
                if current_price >= tp1_price:
                    return True, "take_profit_1"
            else:  # short
                if current_price <= tp1_price:
                    return True, "take_profit_1"
        
        # Chandelier exit (if enabled)
        if exit_plan.use_chandelier:
            chandelier_exit_price = await self._calculate_chandelier_exit(symbol, signal.entry.side, exit_plan)
            
            if signal.entry.side == "buy":
                if current_price <= chandelier_exit_price:
                    return True, "chandelier_exit"
            else:  # short
                if current_price >= chandelier_exit_price:
                    return True, "chandelier_exit"
        
        # Time-based exit
        entry_time = position_info['entry_time']
        time_in_position = datetime.now() - entry_time
        max_time = timedelta(minutes=exit_plan.time_exit_bars * 15)  # Assuming 15-minute bars
        
        if time_in_position >= max_time:
            return True, "time_exit"
        
        return False, ""
    
    async def _execute_enhanced_exit(self, symbol: str, position_info: Dict, current_price: float, exit_reason: str):
        """Execute enhanced exit with tax tracking"""
        
        try:
            execution_result = position_info['execution_result']
            position_size = execution_result.filled_size
            
            # Create exit order
            exit_order = EnhancedOrder(
                order_id=f"exit_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                symbol=symbol,
                side="sell" if position_info['signal'].entry.side == "buy" else "cover",
                size=position_size,
                order_type=OrderType.MARKET,  # Market exit for speed
                target_price=current_price
            )
            
            # Execute exit
            if self.execution_engine:
                exit_result = await self.execution_engine.execute_order(exit_order)
                
                if exit_result.status.value in ['filled', 'partially_filled']:
                    # Calculate PnL
                    entry_price = execution_result.metrics.average_fill_price
                    exit_price = exit_result.metrics.average_fill_price or current_price
                    
                    if position_info['signal'].entry.side == "buy":
                        gross_pnl = (exit_price - entry_price) * position_size
                    else:  # short
                        gross_pnl = (entry_price - exit_price) * position_size
                    
                    total_fees = execution_result.metrics.total_fees + exit_result.metrics.total_fees
                    net_pnl = gross_pnl - total_fees
                    
                    # Register exit with risk manager
                    self.risk_manager.register_enhanced_exit(
                        symbol=symbol,
                        exit_price=exit_price,
                        exit_size=exit_result.filled_size,
                        realized_pnl_quote=net_pnl,
                        closed_at=datetime.now(),
                        actual_exit_fees=exit_result.metrics.total_fees
                    )
                    
                    # Record with tax engine
                    self.tax_engine.record_disposal(
                        symbol=symbol,
                        quantity=exit_result.filled_size,
                        price=exit_price,
                        timestamp=datetime.now(),
                        fees=exit_result.metrics.total_fees,
                        transaction_id=exit_order.order_id
                    )
                    
                    # Calculate fee-adjusted R-multiple
                    r_multiple = self.tax_engine.calculate_fee_adjusted_r_multiple(
                        entry_price=entry_price,
                        exit_price=exit_price,
                        entry_fees=execution_result.metrics.total_fees,
                        exit_fees=exit_result.metrics.total_fees,
                        stop_price=position_info['signal'].exit_plan.stop_price,
                        side="long" if position_info['signal'].entry.side == "buy" else "short"
                    )
                    
                    # Record trade execution
                    self.monitor.record_trade_execution(
                        symbol=symbol,
                        side=position_info['signal'].entry.side,
                        strategy=position_info['signal'].entry.tag,
                        pnl=float(net_pnl),
                        fees=float(total_fees)
                    )
                    
                    logger.info(f"✅ Position closed: {symbol} {exit_reason} "
                               f"PnL=${net_pnl:.2f} R-mult={r_multiple:.2f} "
                               f"Fees=${total_fees:.2f}")
                
            else:
                logger.warning("⚠️ Execution engine not available for exit")
                
        except Exception as e:
            logger.error(f"❌ Enhanced exit execution failed for {symbol}: {e}")
    
    # Helper methods (implement these based on your existing infrastructure)
    
    async def _get_current_equity(self) -> float:
        """Get current total equity"""
        # Implement with your existing BinanceConnector
        # return self.binance_connector.get_total_equity()
        return 10000.0  # Placeholder
    
    async def _calculate_market_volatility(self, market_data: Dict) -> float:
        """Calculate overall market volatility"""
        # Calculate VIX-like volatility across all symbols
        return 1.2  # Placeholder
    
    async def _calculate_symbol_correlation(self, symbol: str) -> float:
        """Calculate correlation with existing positions"""
        # Implement correlation calculation
        return 0.3  # Placeholder
    
    async def _get_current_atr(self, symbol: str) -> float:
        """Get current ATR for symbol"""
        # Implement ATR calculation
        return 100.0  # Placeholder
    
    async def _get_current_price(self, symbol: str) -> float:
        """Get current price for symbol"""
        # Implement price fetching
        return 50000.0  # Placeholder
    
    async def _calculate_chandelier_exit(self, symbol: str, side: str, exit_plan) -> float:
        """Calculate chandelier exit price"""
        # Implement chandelier exit calculation
        return 49000.0  # Placeholder
    
    async def _update_monitoring_metrics(self, equity: float):
        """Update monitoring metrics"""
        
        # Get current performance metrics
        performance_metrics = self.risk_manager.get_performance_summary()
        
        # Update monitoring system
        self.monitor.update_trading_metrics(
            equity=equity,
            daily_start_equity=self.risk_manager.start_of_day_equity,
            portfolio_heat=self.risk_manager.current_portfolio_heat(),
            performance_metrics=performance_metrics,
            open_positions=self.active_positions,
            trading_enabled=self.risk_manager.trading_enabled
        )
    
    def run_backtesting_analysis(self, historical_data: Dict):
        """Run comprehensive backtesting analysis"""
        
        logger.info("🔬 Running comprehensive backtesting analysis...")
        
        # Run backtesting for each major symbol
        results = {}
        
        for symbol, data in historical_data.items():
            if len(data) < 1000:  # Ensure sufficient data
                continue
                
            try:
                symbol_results = run_comprehensive_backtest(data)
                results[symbol] = symbol_results
                
                logger.info(f"✅ Backtesting completed for {symbol}")
                
            except Exception as e:
                logger.error(f"❌ Backtesting failed for {symbol}: {e}")
        
        return results
    
    def generate_tax_report(self, year: int):
        """Generate comprehensive tax report"""
        
        logger.info(f"📄 Generating tax report for {year}...")
        
        try:
            # Generate tax summary
            tax_summary = self.tax_engine.generate_tax_summary(year)
            
            # Export for tax software
            csv_file = self.tax_engine.export_for_tax_software(year, "csv")
            
            logger.info(f"✅ Tax report generated: {csv_file}")
            logger.info(f"📊 Tax Summary:")
            logger.info(f"  Total Gain/Loss: ${tax_summary.short_term_gain_loss + tax_summary.long_term_gain_loss:.2f}")
            logger.info(f"  Short-term: ${tax_summary.short_term_gain_loss:.2f}")
            logger.info(f"  Long-term: ${tax_summary.long_term_gain_loss:.2f}")
            logger.info(f"  Total Fees: ${tax_summary.total_fees:.2f}")
            
            return tax_summary, csv_file
            
        except Exception as e:
            logger.error(f"❌ Tax report generation failed: {e}")
            return None, None


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

async def main():
    """Example of how to use the ultra-aggressive trading bot"""
    
    # Initialize the enhanced bot
    bot = UltraAggresiveTradingBot("config/ultra_aggressive.yaml")
    
    # Mock market data (replace with your actual data fetching)
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]  # Use all 183 pairs in production
    mock_market_data = {
        symbol: None  # Replace with actual OHLCV DataFrames
        for symbol in symbols
    }
    
    # Initialize execution engine (replace with your actual connectors)
    # await bot.initialize_execution_engine(market_data_provider, exchange_connector)
    
    # Run enhanced trading cycle
    try:
        await bot.run_enhanced_trading_cycle(symbols, mock_market_data)
        
        # Generate daily performance report
        performance = bot.risk_manager.get_performance_summary()
        logger.info(f"📊 Daily Performance: {performance}")
        
        # Generate tax report (monthly)
        if datetime.now().day == 1:  # First day of month
            tax_summary, tax_file = bot.generate_tax_report(datetime.now().year)
        
    except Exception as e:
        logger.error(f"❌ Trading cycle failed: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())