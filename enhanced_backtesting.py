"""
Enhanced Backtesting Framework with Backtrader Integration
========================================================

Features:
- Backtrader integration for strategy optimization
- Monte Carlo simulation for parameter robustness
- Walk-forward analysis
- Strategy performance comparison
- Risk-adjusted metrics
- Portfolio-level backtesting
"""

import backtrader as bt
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
import itertools
from concurrent.futures import ProcessPoolExecutor
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

@dataclass
class BacktestConfig:
    """Configuration for backtesting"""
    initial_cash: float = 100000.0
    commission: float = 0.001  # 0.1%
    slippage: float = 0.0005  # 0.05%
    
    # Data parameters
    start_date: str = "2022-01-01"
    end_date: str = "2024-01-01"
    timeframe: str = "1h"  # 1h, 4h, 1d
    
    # Optimization parameters
    optimization_metric: str = "sharpe_ratio"  # sharpe_ratio, return_drawdown_ratio, total_return
    walk_forward_periods: int = 12  # Number of walk-forward periods
    
    # Monte Carlo parameters
    monte_carlo_runs: int = 1000
    parameter_variation: float = 0.2  # 20% variation in parameters

@dataclass
class BacktestResults:
    """Results from a single backtest run"""
    strategy_name: str
    parameters: Dict[str, Any]
    
    # Performance metrics
    total_return: float = 0.0
    annualized_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # Trading metrics
    total_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_trade_return: float = 0.0
    
    # Risk metrics
    volatility: float = 0.0
    var_95: float = 0.0  # Value at Risk 95%
    
    # Execution details
    final_portfolio_value: float = 0.0
    trades: List[Dict] = field(default_factory=list)
    equity_curve: pd.Series = field(default_factory=lambda: pd.Series())

class EnhancedStrategy(bt.Strategy):
    """Enhanced Backtrader strategy integrating our trading rules"""
    
    params = (
        ('atr_period', 14),
        ('stop_atr_mult', 2.5),
        ('trail_atr_mult', 2.0),
        ('partial_tp_r', 1.5),
        ('tp2_r', 3.0),
        ('risk_per_trade', 0.02),
        ('max_positions', 5),
        
        # Enhanced parameters
        ('use_macd_confirmation', True),
        ('use_volatility_filter', True),
        ('volatility_threshold', 1.5),
        ('enable_short_selling', False),
        ('correlation_threshold', 0.7),
        
        # Regime detection
        ('use_ml_regime', False),
        ('adx_trend_threshold', 22.0),
        ('crash_threshold', -0.06),
    )
    
    def __init__(self):
        # Technical indicators
        self.atr = bt.indicators.ATR(period=self.params.atr_period)
        self.rsi = bt.indicators.RSI(period=14)
        self.adx = bt.indicators.DirectionalIndicator(period=14)
        self.ema_fast = bt.indicators.EMA(period=20)
        self.ema_mid = bt.indicators.EMA(period=50)
        self.ema_slow = bt.indicators.EMA(period=200)
        
        # MACD for confirmation
        if self.params.use_macd_confirmation:
            self.macd = bt.indicators.MACD()
        
        # Bollinger Bands
        self.bollinger = bt.indicators.BollingerBands(period=20, devfactor=2.0)
        
        # Donchian Channels
        self.donchian_high = bt.indicators.Highest(self.data.high, period=20)
        self.donchian_low = bt.indicators.Lowest(self.data.low, period=20)
        
        # Position tracking
        self.positions_data = {}
        self.trade_count = 0
        
    def next(self):
        """Main strategy logic"""
        
        # Skip if not enough data
        if len(self.data) < max(200, self.params.atr_period + 10):
            return
        
        current_price = self.data.close[0]
        
        # Position management for existing positions
        self._manage_positions()
        
        # Check for new entries if not at max positions
        if len([pos for pos in self.broker.positions if pos.size != 0]) < self.params.max_positions:
            self._check_entry_signals(current_price)
    
    def _manage_positions(self):
        """Manage existing positions"""
        for data_name, position_info in list(self.positions_data.items()):
            if self.getposition().size == 0:
                # Position was closed, clean up
                if data_name in self.positions_data:
                    del self.positions_data[data_name]
                continue
            
            current_price = self.data.close[0]
            entry_price = position_info.get('entry_price', current_price)
            
            # Update trailing stop
            if self.getposition().size > 0:  # Long position
                trail_stop = current_price - self.atr[0] * self.params.trail_atr_mult
                if trail_stop > position_info.get('stop_price', 0):
                    position_info['stop_price'] = trail_stop
                
                # Check stop loss
                if current_price <= position_info.get('stop_price', 0):
                    self.close()
                    if data_name in self.positions_data:
                        del self.positions_data[data_name]
                
                # Check take profit levels
                R = entry_price - position_info.get('initial_stop', entry_price)
                tp1_price = entry_price + R * self.params.partial_tp_r
                tp2_price = entry_price + R * self.params.tp2_r
                
                if current_price >= tp1_price and not position_info.get('tp1_hit', False):
                    # Take partial profit
                    self.sell(size=self.getposition().size // 3)
                    position_info['tp1_hit'] = True
                
                elif current_price >= tp2_price and not position_info.get('tp2_hit', False):
                    # Take second partial profit
                    self.sell(size=self.getposition().size // 2)
                    position_info['tp2_hit'] = True
    
    def _check_entry_signals(self, current_price):
        """Check for entry signals"""
        
        # Detect market regime
        regime = self._detect_regime()
        
        # Generate signals based on regime
        if regime == "trend":
            self._check_momentum_signals(current_price)
            self._check_breakout_signals(current_price)
        elif regime == "range":
            self._check_mean_reversion_signals(current_price)
    
    def _detect_regime(self) -> str:
        """Detect market regime"""
        # Simplified regime detection
        ema_slope = (self.ema_slow[0] - self.ema_slow[-30]) / self.ema_slow[-30] if len(self.data) > 30 else 0
        adx_value = self.adx[0] if len(self.adx) > 0 else 20
        
        if ema_slope <= self.params.crash_threshold:
            return "crash"
        elif ema_slope > 0 and adx_value >= self.params.adx_trend_threshold:
            return "trend"
        else:
            return "range"
    
    def _check_momentum_signals(self, current_price):
        """Check momentum strategy signals"""
        
        # Momentum conditions
        trend_alignment = (current_price > self.ema_slow[0] and 
                          self.ema_mid[0] > self.ema_slow[0])
        
        momentum_breakout = (self.data.close[-1] <= self.ema_fast[-1] and 
                           current_price > self.ema_fast[0])
        
        strong_trend = self.adx[0] >= self.params.adx_trend_threshold
        
        # Volatility filter
        volatility_ok = True
        if self.params.use_volatility_filter:
            atr_ratio = self.atr[0] / self.atr.sma(20)[0] if self.atr.sma(20)[0] > 0 else 1
            volatility_ok = atr_ratio > self.params.volatility_threshold
        
        # MACD confirmation
        macd_ok = True
        if self.params.use_macd_confirmation and hasattr(self, 'macd'):
            macd_ok = self.macd.macd[0] > self.macd.signal[0]
        
        if trend_alignment and momentum_breakout and strong_trend and volatility_ok and macd_ok:
            self._enter_long_position(current_price, "momentum")
    
    def _check_breakout_signals(self, current_price):
        """Check breakout strategy signals"""
        
        # Breakout conditions
        breakout_high = current_price > self.donchian_high[-1]
        strong_momentum = self.adx[0] >= 20
        
        if breakout_high and strong_momentum:
            self._enter_long_position(current_price, "breakout")
    
    def _check_mean_reversion_signals(self, current_price):
        """Check mean reversion strategy signals"""
        
        # Mean reversion conditions
        oversold_bounce = (self.data.close[-1] < self.bollinger.bot[-1] and 
                          current_price > self.bollinger.bot[0])
        
        low_trend = self.adx[0] < 18
        oversold_rsi = self.rsi[0] < 35
        
        # MACD confirmation for mean reversion
        macd_ok = True
        if self.params.use_macd_confirmation and hasattr(self, 'macd'):
            # Look for bullish divergence or crossover
            macd_bullish = (self.macd.macd[-1] <= self.macd.signal[-1] and 
                           self.macd.macd[0] > self.macd.signal[0])
            macd_ok = macd_bullish or self.macd.macd[0] > self.macd.signal[0]
        
        if oversold_bounce and low_trend and oversold_rsi and macd_ok:
            self._enter_long_position(current_price, "mean_reversion")
    
    def _enter_long_position(self, entry_price, strategy_type):
        """Enter long position with risk management"""
        
        if self.getposition().size != 0:
            return  # Already in position
        
        # Calculate position size based on risk
        stop_price = entry_price - self.atr[0] * self.params.stop_atr_mult
        
        if stop_price >= entry_price:
            return  # Invalid stop
        
        risk_amount = self.broker.getcash() * self.params.risk_per_trade
        risk_per_share = entry_price - stop_price
        
        if risk_per_share <= 0:
            return
        
        position_size = risk_amount / risk_per_share
        
        # Limit position size to available cash
        max_size = (self.broker.getcash() * 0.95) // entry_price
        position_size = min(position_size, max_size)
        
        if position_size > 0:
            self.buy(size=position_size)
            
            # Track position
            self.positions_data[self.data._name] = {
                'entry_price': entry_price,
                'initial_stop': stop_price,
                'stop_price': stop_price,
                'strategy': strategy_type,
                'tp1_hit': False,
                'tp2_hit': False
            }
            
            self.trade_count += 1

class ParameterOptimizer:
    """Parameter optimization using backtrader"""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
    
    def optimize_parameters(self, data: pd.DataFrame, param_ranges: Dict[str, List]) -> List[BacktestResults]:
        """Optimize strategy parameters"""
        
        cerebro = bt.Cerebro(maxcpus=None)  # Use all CPUs
        
        # Add data
        data_feed = bt.feeds.PandasData(dataname=data)
        cerebro.adddata(data_feed)
        
        # Add strategy with parameter optimization
        cerebro.optstrategy(EnhancedStrategy, **param_ranges)
        
        # Set initial cash and commission
        cerebro.broker.setcash(self.config.initial_cash)
        cerebro.broker.setcommission(commission=self.config.commission)
        
        # Add analyzers
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        
        logger.info("Starting parameter optimization...")
        
        # Run optimization
        opt_runs = cerebro.run()
        
        results = []
        
        for run in opt_runs:
            for strategy in run:
                # Extract parameters
                params = {name: getattr(strategy.params, name) 
                         for name in dir(strategy.params) 
                         if not name.startswith('_')}
                
                # Extract performance metrics
                analyzers = strategy.analyzers
                
                sharpe = analyzers.sharpe.get_analysis().get('sharperatio', 0)
                drawdown = analyzers.drawdown.get_analysis()
                returns = analyzers.returns.get_analysis()
                trades = analyzers.trades.get_analysis()
                
                result = BacktestResults(
                    strategy_name="EnhancedStrategy",
                    parameters=params,
                    total_return=returns.get('rtot', 0),
                    annualized_return=returns.get('rnorm100', 0),
                    max_drawdown=drawdown.get('max', {}).get('drawdown', 0),
                    sharpe_ratio=sharpe or 0,
                    total_trades=trades.get('total', {}).get('total', 0),
                    win_rate=(trades.get('won', {}).get('total', 0) / 
                             max(trades.get('total', {}).get('total', 1), 1)) * 100,
                    final_portfolio_value=strategy.broker.getvalue()
                )
                
                results.append(result)
        
        # Sort by optimization metric
        if self.config.optimization_metric == "sharpe_ratio":
            results.sort(key=lambda x: x.sharpe_ratio, reverse=True)
        elif self.config.optimization_metric == "total_return":
            results.sort(key=lambda x: x.total_return, reverse=True)
        elif self.config.optimization_metric == "return_drawdown_ratio":
            results.sort(key=lambda x: x.total_return / max(abs(x.max_drawdown), 0.01), reverse=True)
        
        logger.info(f"Optimization completed. Best result: {results[0].sharpe_ratio:.3f} Sharpe")
        
        return results

class MonteCarloSimulator:
    """Monte Carlo simulation for parameter robustness testing"""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
    
    def run_monte_carlo(self, data: pd.DataFrame, base_params: Dict[str, Any]) -> Dict[str, Any]:
        """Run Monte Carlo simulation with parameter variations"""
        
        logger.info(f"Running {self.config.monte_carlo_runs} Monte Carlo simulations...")
        
        results = []
        
        for i in range(self.config.monte_carlo_runs):
            # Generate parameter variations
            varied_params = self._vary_parameters(base_params)
            
            # Run single backtest
            result = self._run_single_backtest(data, varied_params)
            results.append(result)
            
            if (i + 1) % 100 == 0:
                logger.info(f"Completed {i + 1}/{self.config.monte_carlo_runs} simulations")
        
        # Analyze results
        analysis = self._analyze_monte_carlo_results(results)
        
        return analysis
    
    def _vary_parameters(self, base_params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate parameter variations"""
        varied = base_params.copy()
        
        for param, value in base_params.items():
            if isinstance(value, (int, float)) and param != 'max_positions':
                # Apply random variation
                variation = np.random.normal(1.0, self.config.parameter_variation)
                varied[param] = max(value * variation, 0.01)  # Ensure positive values
        
        return varied
    
    def _run_single_backtest(self, data: pd.DataFrame, params: Dict[str, Any]) -> BacktestResults:
        """Run single backtest with given parameters"""
        
        cerebro = bt.Cerebro()
        
        # Add data
        data_feed = bt.feeds.PandasData(dataname=data)
        cerebro.adddata(data_feed)
        
        # Add strategy with specific parameters
        cerebro.addstrategy(EnhancedStrategy, **params)
        
        # Set broker parameters
        cerebro.broker.setcash(self.config.initial_cash)
        cerebro.broker.setcommission(commission=self.config.commission)
        
        # Add analyzers
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        
        # Run backtest
        results = cerebro.run()
        strategy = results[0]
        
        # Extract metrics
        analyzers = strategy.analyzers
        sharpe = analyzers.sharpe.get_analysis().get('sharperatio', 0)
        drawdown = analyzers.drawdown.get_analysis()
        returns = analyzers.returns.get_analysis()
        trades = analyzers.trades.get_analysis()
        
        return BacktestResults(
            strategy_name="EnhancedStrategy",
            parameters=params,
            total_return=returns.get('rtot', 0),
            annualized_return=returns.get('rnorm100', 0),
            max_drawdown=drawdown.get('max', {}).get('drawdown', 0),
            sharpe_ratio=sharpe or 0,
            total_trades=trades.get('total', {}).get('total', 0),
            win_rate=(trades.get('won', {}).get('total', 0) / 
                     max(trades.get('total', {}).get('total', 1), 1)) * 100,
            final_portfolio_value=strategy.broker.getvalue()
        )
    
    def _analyze_monte_carlo_results(self, results: List[BacktestResults]) -> Dict[str, Any]:
        """Analyze Monte Carlo results"""
        
        sharpe_ratios = [r.sharpe_ratio for r in results if r.sharpe_ratio is not None]
        returns = [r.total_return for r in results if r.total_return is not None]
        max_drawdowns = [r.max_drawdown for r in results if r.max_drawdown is not None]
        
        analysis = {
            'total_runs': len(results),
            'profitable_runs': len([r for r in results if r.total_return > 0]),
            'profitability_rate': len([r for r in results if r.total_return > 0]) / len(results),
            
            'sharpe_ratio': {
                'mean': np.mean(sharpe_ratios) if sharpe_ratios else 0,
                'std': np.std(sharpe_ratios) if sharpe_ratios else 0,
                'percentile_5': np.percentile(sharpe_ratios, 5) if sharpe_ratios else 0,
                'percentile_95': np.percentile(sharpe_ratios, 95) if sharpe_ratios else 0,
                'positive_rate': len([s for s in sharpe_ratios if s > 0]) / len(sharpe_ratios) if sharpe_ratios else 0
            },
            
            'total_return': {
                'mean': np.mean(returns) if returns else 0,
                'std': np.std(returns) if returns else 0,
                'percentile_5': np.percentile(returns, 5) if returns else 0,
                'percentile_95': np.percentile(returns, 95) if returns else 0
            },
            
            'max_drawdown': {
                'mean': np.mean(max_drawdowns) if max_drawdowns else 0,
                'std': np.std(max_drawdowns) if max_drawdowns else 0,
                'percentile_5': np.percentile(max_drawdowns, 5) if max_drawdowns else 0,
                'percentile_95': np.percentile(max_drawdowns, 95) if max_drawdowns else 0
            }
        }
        
        logger.info(f"Monte Carlo Analysis:")
        logger.info(f"  Profitability Rate: {analysis['profitability_rate']:.1%}")
        logger.info(f"  Mean Sharpe Ratio: {analysis['sharpe_ratio']['mean']:.3f}")
        logger.info(f"  Mean Total Return: {analysis['total_return']['mean']:.1%}")
        
        return analysis

class WalkForwardAnalyzer:
    """Walk-forward analysis for out-of-sample testing"""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
    
    def run_walk_forward(self, data: pd.DataFrame, param_ranges: Dict[str, List]) -> Dict[str, Any]:
        """Run walk-forward analysis"""
        
        logger.info(f"Running walk-forward analysis with {self.config.walk_forward_periods} periods")
        
        # Split data into periods
        total_periods = self.config.walk_forward_periods
        period_length = len(data) // total_periods
        
        results = []
        
        for i in range(total_periods - 1):  # Leave last period for out-of-sample
            # In-sample period (for optimization)
            is_start = i * period_length
            is_end = (i + 1) * period_length
            in_sample_data = data.iloc[is_start:is_end]
            
            # Out-of-sample period (for testing)
            oos_start = is_end
            oos_end = min((i + 2) * period_length, len(data))
            out_sample_data = data.iloc[oos_start:oos_end]
            
            # Optimize on in-sample data
            optimizer = ParameterOptimizer(self.config)
            optimization_results = optimizer.optimize_parameters(in_sample_data, param_ranges)
            
            if not optimization_results:
                continue
                
            best_params = optimization_results[0].parameters
            
            # Test on out-of-sample data
            oos_result = self._run_single_backtest(out_sample_data, best_params)
            
            results.append({
                'period': i + 1,
                'in_sample_result': optimization_results[0],
                'out_sample_result': oos_result,
                'best_params': best_params
            })
            
            logger.info(f"Period {i + 1}: IS Sharpe={optimization_results[0].sharpe_ratio:.3f}, "
                       f"OOS Sharpe={oos_result.sharpe_ratio:.3f}")
        
        # Analyze walk-forward results
        analysis = self._analyze_walk_forward_results(results)
        
        return analysis
    
    def _run_single_backtest(self, data: pd.DataFrame, params: Dict[str, Any]) -> BacktestResults:
        """Run single backtest (same as MonteCarloSimulator)"""
        
        cerebro = bt.Cerebro()
        
        # Add data
        data_feed = bt.feeds.PandasData(dataname=data)
        cerebro.adddata(data_feed)
        
        # Add strategy with specific parameters
        cerebro.addstrategy(EnhancedStrategy, **params)
        
        # Set broker parameters
        cerebro.broker.setcash(self.config.initial_cash)
        cerebro.broker.setcommission(commission=self.config.commission)
        
        # Add analyzers
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        
        # Run backtest
        results = cerebro.run()
        strategy = results[0]
        
        # Extract metrics
        analyzers = strategy.analyzers
        sharpe = analyzers.sharpe.get_analysis().get('sharperatio', 0)
        drawdown = analyzers.drawdown.get_analysis()
        returns = analyzers.returns.get_analysis()
        trades = analyzers.trades.get_analysis()
        
        return BacktestResults(
            strategy_name="EnhancedStrategy",
            parameters=params,
            total_return=returns.get('rtot', 0),
            annualized_return=returns.get('rnorm100', 0),
            max_drawdown=drawdown.get('max', {}).get('drawdown', 0),
            sharpe_ratio=sharpe or 0,
            total_trades=trades.get('total', {}).get('total', 0),
            win_rate=(trades.get('won', {}).get('total', 0) / 
                     max(trades.get('total', {}).get('total', 1), 1)) * 100,
            final_portfolio_value=strategy.broker.getvalue()
        )
    
    def _analyze_walk_forward_results(self, results: List[Dict]) -> Dict[str, Any]:
        """Analyze walk-forward results"""
        
        is_sharpes = [r['in_sample_result'].sharpe_ratio for r in results if r['in_sample_result'].sharpe_ratio is not None]
        oos_sharpes = [r['out_sample_result'].sharpe_ratio for r in results if r['out_sample_result'].sharpe_ratio is not None]
        
        is_returns = [r['in_sample_result'].total_return for r in results if r['in_sample_result'].total_return is not None]
        oos_returns = [r['out_sample_result'].total_return for r in results if r['out_sample_result'].total_return is not None]
        
        analysis = {
            'total_periods': len(results),
            'profitable_oos_periods': len([r for r in oos_returns if r > 0]),
            'oos_profitability_rate': len([r for r in oos_returns if r > 0]) / len(oos_returns) if oos_returns else 0,
            
            'in_sample_performance': {
                'mean_sharpe': np.mean(is_sharpes) if is_sharpes else 0,
                'mean_return': np.mean(is_returns) if is_returns else 0
            },
            
            'out_sample_performance': {
                'mean_sharpe': np.mean(oos_sharpes) if oos_sharpes else 0,
                'mean_return': np.mean(oos_returns) if oos_returns else 0
            },
            
            'degradation': {
                'sharpe_degradation': (np.mean(is_sharpes) - np.mean(oos_sharpes)) / max(np.mean(is_sharpes), 0.01) if is_sharpes and oos_sharpes else 0,
                'return_degradation': (np.mean(is_returns) - np.mean(oos_returns)) / max(np.mean(is_returns), 0.01) if is_returns and oos_returns else 0
            },
            
            'consistency': {
                'sharpe_correlation': np.corrcoef(is_sharpes, oos_sharpes)[0, 1] if len(is_sharpes) > 1 and len(oos_sharpes) > 1 else 0,
                'return_correlation': np.corrcoef(is_returns, oos_returns)[0, 1] if len(is_returns) > 1 and len(oos_returns) > 1 else 0
            }
        }
        
        logger.info(f"Walk-Forward Analysis:")
        logger.info(f"  OOS Profitability Rate: {analysis['oos_profitability_rate']:.1%}")
        logger.info(f"  Sharpe Degradation: {analysis['degradation']['sharpe_degradation']:.1%}")
        logger.info(f"  Performance Correlation: {analysis['consistency']['sharpe_correlation']:.3f}")
        
        return analysis

# ============================================================================
# USAGE EXAMPLE
# ============================================================================

def run_comprehensive_backtest(data: pd.DataFrame) -> Dict[str, Any]:
    """Run comprehensive backtesting analysis"""
    
    config = BacktestConfig(
        initial_cash=100000.0,
        commission=0.001,
        walk_forward_periods=8,
        monte_carlo_runs=500
    )
    
    # Define parameter ranges for optimization
    param_ranges = {
        'atr_period': [10, 14, 20],
        'stop_atr_mult': [2.0, 2.5, 3.0],
        'trail_atr_mult': [1.5, 2.0, 2.5],
        'partial_tp_r': [1.0, 1.5, 2.0],
        'tp2_r': [2.5, 3.0, 4.0],
        'risk_per_trade': [0.01, 0.02, 0.03]
    }
    
    results = {}
    
    # 1. Parameter Optimization
    logger.info("1. Running parameter optimization...")
    optimizer = ParameterOptimizer(config)
    optimization_results = optimizer.optimize_parameters(data, param_ranges)
    results['optimization'] = optimization_results[:10]  # Top 10 results
    
    # 2. Monte Carlo Simulation with best parameters
    if optimization_results:
        logger.info("2. Running Monte Carlo simulation...")
        best_params = optimization_results[0].parameters
        mc_simulator = MonteCarloSimulator(config)
        mc_results = mc_simulator.run_monte_carlo(data, best_params)
        results['monte_carlo'] = mc_results
    
    # 3. Walk-Forward Analysis
    logger.info("3. Running walk-forward analysis...")
    wf_analyzer = WalkForwardAnalyzer(config)
    wf_results = wf_analyzer.run_walk_forward(data, param_ranges)
    results['walk_forward'] = wf_results
    
    return results

if __name__ == "__main__":
    # Example usage with mock data
    dates = pd.date_range('2022-01-01', '2024-01-01', freq='1H')
    np.random.seed(42)
    
    # Generate synthetic OHLCV data
    prices = 50000 + np.cumsum(np.random.randn(len(dates)) * 100)
    
    mock_data = pd.DataFrame({
        'open': prices + np.random.randn(len(dates)) * 50,
        'high': prices + abs(np.random.randn(len(dates)) * 100),
        'low': prices - abs(np.random.randn(len(dates)) * 100), 
        'close': prices,
        'volume': np.random.randint(100, 1000, len(dates))
    }, index=dates)
    
    # Ensure OHLC consistency
    mock_data['high'] = mock_data[['open', 'high', 'close']].max(axis=1)
    mock_data['low'] = mock_data[['open', 'low', 'close']].min(axis=1)
    
    print("Running comprehensive backtest analysis...")
    comprehensive_results = run_comprehensive_backtest(mock_data)
    
    print("\n=== BACKTEST RESULTS ===")
    
    if 'optimization' in comprehensive_results:
        best_result = comprehensive_results['optimization'][0]
        print(f"\nBest Strategy Performance:")
        print(f"  Sharpe Ratio: {best_result.sharpe_ratio:.3f}")
        print(f"  Total Return: {best_result.total_return:.1%}")
        print(f"  Max Drawdown: {best_result.max_drawdown:.1%}")
        print(f"  Win Rate: {best_result.win_rate:.1f}%")
    
    if 'monte_carlo' in comprehensive_results:
        mc_results = comprehensive_results['monte_carlo']
        print(f"\nMonte Carlo Robustness:")
        print(f"  Profitability Rate: {mc_results['profitability_rate']:.1%}")
        print(f"  Mean Sharpe: {mc_results['sharpe_ratio']['mean']:.3f} ± {mc_results['sharpe_ratio']['std']:.3f}")
    
    if 'walk_forward' in comprehensive_results:
        wf_results = comprehensive_results['walk_forward']
        print(f"\nWalk-Forward Validation:")
        print(f"  OOS Profitability: {wf_results['oos_profitability_rate']:.1%}")
        print(f"  Performance Degradation: {wf_results['degradation']['sharpe_degradation']:.1%}")
        print(f"  Consistency: {wf_results['consistency']['sharpe_correlation']:.3f}")
    
    print("\nBacktesting analysis completed!")