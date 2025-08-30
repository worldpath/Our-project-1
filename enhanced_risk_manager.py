"""
Enhanced Risk Manager with Dynamic Risk Adjustment
=================================================

Implements all recommended risk management upgrades:
- Dynamic risk_per_trade scaling based on equity performance
- Volatility-based position sizing using ATR multiplier
- Enhanced correlation management
- PNL threshold alerts
- Advanced drawdown protection
- Fee-adjusted R-multiple calculations
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable
from datetime import datetime, date, timedelta
import json
import numpy as np
import pandas as pd
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    """Dynamic risk levels based on performance"""
    CONSERVATIVE = "conservative"
    NORMAL = "normal" 
    AGGRESSIVE = "aggressive"
    MAXIMUM = "maximum"

@dataclass
class EnhancedPosition:
    """Enhanced position with fee tracking and volatility metrics"""
    symbol: str
    entry_price: float
    stop_price: float
    size_units: float
    opened_at: datetime
    tag: str = ""
    
    # Enhanced fields
    per_trade_risk_quote: float = 0.0
    entry_fees: float = 0.0
    atr_at_entry: float = 0.0
    volatility_multiplier: float = 1.0
    correlation_at_entry: float = 0.0
    expected_exit_fees: float = 0.0
    
    # Side tracking for short positions
    side: str = "long"  # "long" or "short"
    
    def unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized PnL including fees"""
        if self.side == "long":
            gross_pnl = (current_price - self.entry_price) * self.size_units
        else:  # short
            gross_pnl = (self.entry_price - current_price) * self.size_units
            
        # Subtract entry fees already paid and expected exit fees
        net_pnl = gross_pnl - self.entry_fees - self.expected_exit_fees
        return net_pnl
    
    def fee_adjusted_r_multiple(self, current_price: float) -> float:
        """Calculate R-multiple adjusted for fees"""
        initial_risk = abs(self.entry_price - self.stop_price) * self.size_units
        if initial_risk <= 0:
            return 0.0
            
        unrealized = self.unrealized_pnl(current_price)
        return unrealized / initial_risk

@dataclass
class PerformanceMetrics:
    """Track performance metrics for dynamic risk scaling"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    current_win_streak: int = 0
    current_loss_streak: int = 0
    
    # Volatility metrics
    daily_returns: List[float] = field(default_factory=list)
    sharpe_ratio: float = 0.0
    max_drawdown_pct: float = 0.0
    
    def win_rate(self) -> float:
        """Calculate win rate percentage"""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100
    
    def average_win(self) -> float:
        """Average win amount"""
        if self.winning_trades == 0:
            return 0.0
        # This is simplified - in practice, track individual trade PnL
        return self.total_pnl / self.winning_trades if self.winning_trades > 0 else 0.0
    
    def profit_factor(self) -> float:
        """Profit factor (gross profit / gross loss)"""
        # Simplified calculation
        if self.losing_trades == 0:
            return float('inf') if self.total_pnl > 0 else 0.0
        return max(0.0, self.total_pnl / abs(self.total_pnl * (self.losing_trades / max(self.total_trades, 1))))

@dataclass 
class DynamicRiskConfig:
    """Configuration for dynamic risk scaling"""
    base_risk_per_trade: float = 0.02  # 2% base risk
    min_risk_per_trade: float = 0.005  # 0.5% minimum risk
    max_risk_per_trade: float = 0.05   # 5% maximum risk
    
    # Performance thresholds for risk scaling
    win_rate_threshold_high: float = 70.0  # Scale up risk if win rate > 70%
    win_rate_threshold_low: float = 40.0   # Scale down risk if win rate < 40%
    
    profit_factor_threshold_high: float = 2.0  # Scale up if profit factor > 2.0
    profit_factor_threshold_low: float = 1.2   # Scale down if profit factor < 1.2
    
    # Consecutive trade thresholds
    max_consecutive_losses_before_reduction: int = 3
    consecutive_wins_before_increase: int = 5
    
    # Risk scaling factors
    performance_scaling_factor: float = 0.5  # How much to scale by
    volatility_scaling_enabled: bool = True
    correlation_scaling_enabled: bool = True

@dataclass
class EnhancedRiskManager:
    """Enhanced Risk Manager with all advanced features"""
    
    # Basic risk parameters
    max_portfolio_heat: float = 0.10
    max_daily_loss: float = 0.05
    max_drawdown: float = 0.25
    max_concurrent: int = 3
    
    # Enhanced parameters
    correlation_gate: bool = True
    corr_threshold: float = 0.60
    volatility_adjustment: bool = True
    dynamic_risk_scaling: bool = True
    
    # Fee calculations
    maker_fee_rate: float = 0.001  # 0.1% maker fee
    taker_fee_rate: float = 0.0015  # 0.15% taker fee
    
    # State management
    state_path: str = "enhanced_risk_state.json"
    
    # Dynamic components
    dynamic_config: DynamicRiskConfig = field(default_factory=DynamicRiskConfig)
    performance_metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    
    # Position tracking
    open_positions: Dict[str, EnhancedPosition] = field(default_factory=dict)
    
    # Equity tracking
    equity_peak: float = 0.0
    today: Optional[date] = None
    start_of_day_equity: float = 0.0
    realized_pnl_today: float = 0.0
    trading_enabled: bool = True
    
    # PnL alerts
    daily_pnl_alert_threshold: float = -0.10  # Alert at -10% daily loss
    pnl_alert_callback: Optional[Callable[[str], None]] = None
    
    def __post_init__(self):
        """Initialize enhanced components"""
        self._load()
    
    def set_pnl_alert_callback(self, callback: Callable[[str], None]):
        """Set callback function for PnL alerts"""
        self.pnl_alert_callback = callback
    
    def _save(self):
        """Save enhanced state to JSON"""
        state = {
            "equity_peak": self.equity_peak,
            "today": self.today.isoformat() if self.today else None,
            "start_of_day_equity": self.start_of_day_equity,
            "realized_pnl_today": self.realized_pnl_today,
            "trading_enabled": self.trading_enabled,
            
            # Enhanced state
            "performance_metrics": {
                "total_trades": self.performance_metrics.total_trades,
                "winning_trades": self.performance_metrics.winning_trades,
                "losing_trades": self.performance_metrics.losing_trades,
                "total_pnl": self.performance_metrics.total_pnl,
                "max_consecutive_wins": self.performance_metrics.max_consecutive_wins,
                "max_consecutive_losses": self.performance_metrics.max_consecutive_losses,
                "current_win_streak": self.performance_metrics.current_win_streak,
                "current_loss_streak": self.performance_metrics.current_loss_streak,
                "daily_returns": self.performance_metrics.daily_returns[-30:],  # Keep last 30 days
                "sharpe_ratio": self.performance_metrics.sharpe_ratio,
                "max_drawdown_pct": self.performance_metrics.max_drawdown_pct
            },
            
            "open_positions": {
                sym: {
                    "entry_price": p.entry_price,
                    "stop_price": p.stop_price,
                    "size_units": p.size_units,
                    "opened_at": p.opened_at.isoformat(),
                    "tag": p.tag,
                    "per_trade_risk_quote": p.per_trade_risk_quote,
                    "entry_fees": p.entry_fees,
                    "atr_at_entry": p.atr_at_entry,
                    "volatility_multiplier": p.volatility_multiplier,
                    "correlation_at_entry": p.correlation_at_entry,
                    "expected_exit_fees": p.expected_exit_fees,
                    "side": p.side
                } for sym, p in self.open_positions.items()
            }
        }
        
        try:
            with open(self.state_path, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save risk manager state: {e}")
    
    def _load(self):
        """Load enhanced state from JSON"""
        try:
            with open(self.state_path, "r") as f:
                state = json.load(f)
            
            # Basic state
            self.equity_peak = state.get("equity_peak", 0.0)
            self.today = date.fromisoformat(state["today"]) if state.get("today") else None
            self.start_of_day_equity = state.get("start_of_day_equity", 0.0)
            self.realized_pnl_today = state.get("realized_pnl_today", 0.0)
            self.trading_enabled = state.get("trading_enabled", True)
            
            # Performance metrics
            perf_data = state.get("performance_metrics", {})
            self.performance_metrics = PerformanceMetrics(
                total_trades=perf_data.get("total_trades", 0),
                winning_trades=perf_data.get("winning_trades", 0),
                losing_trades=perf_data.get("losing_trades", 0),
                total_pnl=perf_data.get("total_pnl", 0.0),
                max_consecutive_wins=perf_data.get("max_consecutive_wins", 0),
                max_consecutive_losses=perf_data.get("max_consecutive_losses", 0),
                current_win_streak=perf_data.get("current_win_streak", 0),
                current_loss_streak=perf_data.get("current_loss_streak", 0),
                daily_returns=perf_data.get("daily_returns", []),
                sharpe_ratio=perf_data.get("sharpe_ratio", 0.0),
                max_drawdown_pct=perf_data.get("max_drawdown_pct", 0.0)
            )
            
            # Positions
            self.open_positions = {}
            for sym, p_data in state.get("open_positions", {}).items():
                self.open_positions[sym] = EnhancedPosition(
                    symbol=sym,
                    entry_price=p_data["entry_price"],
                    stop_price=p_data["stop_price"],
                    size_units=p_data["size_units"],
                    opened_at=datetime.fromisoformat(p_data["opened_at"]),
                    tag=p_data.get("tag", ""),
                    per_trade_risk_quote=p_data.get("per_trade_risk_quote", 0.0),
                    entry_fees=p_data.get("entry_fees", 0.0),
                    atr_at_entry=p_data.get("atr_at_entry", 0.0),
                    volatility_multiplier=p_data.get("volatility_multiplier", 1.0),
                    correlation_at_entry=p_data.get("correlation_at_entry", 0.0),
                    expected_exit_fees=p_data.get("expected_exit_fees", 0.0),
                    side=p_data.get("side", "long")
                )
                
        except Exception as e:
            logger.warning(f"Could not load risk manager state: {e}")
            # Initialize with defaults
            self.performance_metrics = PerformanceMetrics()
            self.open_positions = {}
    
    def on_start(self):
        """Initialize risk manager"""
        self._load()
    
    def flush(self):
        """Save state"""
        self._save()
    
    def calculate_dynamic_risk_per_trade(self, equity: float, market_volatility: float = 1.0) -> float:
        """
        Calculate dynamic risk per trade based on performance and market conditions
        
        Args:
            equity: Current equity
            market_volatility: Market volatility multiplier (default 1.0)
            
        Returns:
            Adjusted risk per trade as fraction of equity
        """
        if not self.dynamic_risk_scaling:
            return self.dynamic_config.base_risk_per_trade
        
        base_risk = self.dynamic_config.base_risk_per_trade
        
        # Performance-based adjustment
        performance_multiplier = 1.0
        
        # Win rate adjustment
        win_rate = self.performance_metrics.win_rate()
        if win_rate > self.dynamic_config.win_rate_threshold_high:
            performance_multiplier *= (1.0 + self.dynamic_config.performance_scaling_factor)
        elif win_rate < self.dynamic_config.win_rate_threshold_low:
            performance_multiplier *= (1.0 - self.dynamic_config.performance_scaling_factor)
        
        # Profit factor adjustment
        profit_factor = self.performance_metrics.profit_factor()
        if profit_factor > self.dynamic_config.profit_factor_threshold_high:
            performance_multiplier *= (1.0 + self.dynamic_config.performance_scaling_factor * 0.5)
        elif profit_factor < self.dynamic_config.profit_factor_threshold_low:
            performance_multiplier *= (1.0 - self.dynamic_config.performance_scaling_factor * 0.5)
        
        # Consecutive loss reduction
        if self.performance_metrics.current_loss_streak >= self.dynamic_config.max_consecutive_losses_before_reduction:
            reduction_factor = 0.5 ** (self.performance_metrics.current_loss_streak - self.dynamic_config.max_consecutive_losses_before_reduction + 1)
            performance_multiplier *= reduction_factor
        
        # Consecutive win increase
        if self.performance_metrics.current_win_streak >= self.dynamic_config.consecutive_wins_before_increase:
            increase_factor = 1.0 + (self.performance_metrics.current_win_streak - self.dynamic_config.consecutive_wins_before_increase + 1) * 0.1
            performance_multiplier *= min(increase_factor, 2.0)  # Cap at 2x
        
        # Volatility adjustment
        if self.dynamic_config.volatility_scaling_enabled:
            # Reduce risk in high volatility environments
            volatility_adjustment = 1.0 / (1.0 + (market_volatility - 1.0) * 0.5)
            performance_multiplier *= volatility_adjustment
        
        # Calculate final risk
        adjusted_risk = base_risk * performance_multiplier
        
        # Apply bounds
        adjusted_risk = max(self.dynamic_config.min_risk_per_trade, 
                          min(self.dynamic_config.max_risk_per_trade, adjusted_risk))
        
        logger.info(f"Dynamic risk calculation: base={base_risk:.3f}, multiplier={performance_multiplier:.3f}, final={adjusted_risk:.3f}")
        
        return adjusted_risk
    
    def calculate_volatility_adjusted_size(self, base_size: float, atr: float, price: float) -> Tuple[float, float]:
        """
        Calculate volatility-adjusted position size using ATR multiplier
        
        Args:
            base_size: Base position size in units
            atr: Average True Range
            price: Current price
            
        Returns:
            (adjusted_size, volatility_multiplier)
        """
        if not self.volatility_adjustment or atr <= 0 or price <= 0:
            return base_size, 1.0
        
        # Calculate ATR as percentage of price
        atr_pct = atr / price
        
        # Define normal volatility (2% ATR)
        normal_atr_pct = 0.02
        
        # Calculate volatility multiplier (inverse relationship)
        volatility_ratio = atr_pct / normal_atr_pct
        volatility_multiplier = 1.0 / np.sqrt(max(volatility_ratio, 0.5))  # Don't reduce too much
        
        # Cap the adjustment
        volatility_multiplier = max(0.5, min(2.0, volatility_multiplier))
        
        adjusted_size = base_size * volatility_multiplier
        
        return adjusted_size, volatility_multiplier
    
    def calculate_fees(self, symbol: str, size: float, price: float, is_maker: bool = False) -> float:
        """Calculate trading fees"""
        fee_rate = self.maker_fee_rate if is_maker else self.taker_fee_rate
        notional_value = size * price
        return notional_value * fee_rate
    
    def on_bar_start(self, now: datetime, equity: float):
        """Enhanced bar start processing with PnL alerts"""
        # Basic daily reset logic
        if self.today != now.date():
            # Calculate daily return for performance tracking
            if self.start_of_day_equity > 0:
                daily_return = (equity - self.start_of_day_equity) / self.start_of_day_equity
                self.performance_metrics.daily_returns.append(daily_return)
                
                # Keep only last 30 days
                if len(self.performance_metrics.daily_returns) > 30:
                    self.performance_metrics.daily_returns = self.performance_metrics.daily_returns[-30:]
                
                # Update Sharpe ratio
                if len(self.performance_metrics.daily_returns) >= 10:
                    returns_array = np.array(self.performance_metrics.daily_returns)
                    if np.std(returns_array) > 0:
                        self.performance_metrics.sharpe_ratio = np.mean(returns_array) / np.std(returns_array) * np.sqrt(365)
            
            self.today = now.date()
            self.start_of_day_equity = equity
            self.realized_pnl_today = 0.0
            self.trading_enabled = True
            self._save()
        
        # Update equity peak
        if equity > self.equity_peak:
            self.equity_peak = equity
            self._save()
        
        # Enhanced risk gates
        if self.equity_peak > 0:
            drawdown_pct = (self.equity_peak - equity) / self.equity_peak
            if drawdown_pct >= self.max_drawdown:
                self.trading_enabled = False
                if self.pnl_alert_callback:
                    self.pnl_alert_callback(f"🚨 MAXIMUM DRAWDOWN HIT: {drawdown_pct:.2%}")
        
        if self.start_of_day_equity > 0:
            daily_pnl_pct = (equity - self.start_of_day_equity) / self.start_of_day_equity
            if daily_pnl_pct <= self.max_daily_loss:
                self.trading_enabled = False
                if self.pnl_alert_callback:
                    self.pnl_alert_callback(f"🚨 DAILY LOSS LIMIT HIT: {daily_pnl_pct:.2%}")
            elif daily_pnl_pct <= self.daily_pnl_alert_threshold:
                if self.pnl_alert_callback:
                    self.pnl_alert_callback(f"⚠️ Daily PnL Alert: {daily_pnl_pct:.2%}")
    
    def current_portfolio_heat(self) -> float:
        """Calculate current portfolio heat including fee adjustments"""
        total_risk = 0.0
        for position in self.open_positions.values():
            # Include fees in risk calculation
            position_risk = position.per_trade_risk_quote + position.entry_fees + position.expected_exit_fees
            total_risk += position_risk
        return total_risk
    
    def _per_trade_risk_quote(self, entry: float, stop: float, size: float, side: str = "long") -> float:
        """Calculate per-trade risk including direction"""
        if side == "long":
            if stop >= entry:
                return 0.0
            return max(0.0, (entry - stop) * size)
        else:  # short
            if stop <= entry:
                return 0.0
            return max(0.0, (stop - entry) * size)
    
    def assess_enhanced_position(self, 
                                symbol: str, 
                                entry_price: float, 
                                stop_price: float, 
                                equity: float,
                                risk_per_trade_fraction: float = None,
                                lot_step: float = 0.000001,
                                avg_pairwise_corr: float = None,
                                atr: float = None,
                                side: str = "long",
                                is_maker_order: bool = False) -> 'EnhancedAssessment':
        """
        Enhanced position assessment with all new features
        """
        
        # Use dynamic risk if not specified
        if risk_per_trade_fraction is None:
            market_volatility = (atr / entry_price) / 0.02 if atr and entry_price > 0 else 1.0
            risk_per_trade_fraction = self.calculate_dynamic_risk_per_trade(equity, market_volatility)
        
        # Basic gates
        if not self.trading_enabled:
            return EnhancedAssessment(
                accept=False, 
                reason="Trading disabled by risk gates", 
                max_size_units=0.0,
                heat_after=self.current_portfolio_heat() / max(equity, 1e-9),
                concurrency_after=len(self.open_positions),
                dynamic_risk_used=risk_per_trade_fraction
            )
        
        if len(self.open_positions) >= self.max_concurrent:
            return EnhancedAssessment(
                accept=False,
                reason=f"Max concurrency {self.max_concurrent} reached",
                max_size_units=0.0,
                heat_after=self.current_portfolio_heat() / max(equity, 1e-9),
                concurrency_after=len(self.open_positions),
                dynamic_risk_used=risk_per_trade_fraction
            )
        
        # Enhanced correlation check
        if (self.correlation_gate and 
            self.dynamic_config.correlation_scaling_enabled and 
            avg_pairwise_corr is not None and 
            avg_pairwise_corr >= self.corr_threshold):
            return EnhancedAssessment(
                accept=False,
                reason=f"Correlation {avg_pairwise_corr:.2f} >= {self.corr_threshold:.2f}",
                max_size_units=0.0,
                heat_after=self.current_portfolio_heat() / max(equity, 1e-9),
                concurrency_after=len(self.open_positions),
                dynamic_risk_used=risk_per_trade_fraction
            )
        
        # Calculate position metrics
        used_heat = self.current_portfolio_heat()
        headroom = max(0.0, self.max_portfolio_heat * equity - used_heat)
        
        risk_per_unit = abs(entry_price - stop_price)
        if risk_per_unit <= 0:
            return EnhancedAssessment(
                accept=False,
                reason="Invalid stop price",
                max_size_units=0.0,
                heat_after=used_heat / max(equity, 1e-9),
                concurrency_after=len(self.open_positions),
                dynamic_risk_used=risk_per_trade_fraction
            )
        
        # Calculate base size
        desired_risk_amount = equity * risk_per_trade_fraction
        base_size = desired_risk_amount / risk_per_unit
        
        # Apply volatility adjustment
        if atr and self.volatility_adjustment:
            adjusted_size, volatility_mult = self.calculate_volatility_adjusted_size(base_size, atr, entry_price)
        else:
            adjusted_size, volatility_mult = base_size, 1.0
        
        # Check against portfolio heat limit
        by_heat_limit = headroom / risk_per_unit if risk_per_unit > 0 else 0.0
        final_size = min(adjusted_size, by_heat_limit)
        
        # Apply lot step
        if lot_step > 0:
            final_size = (final_size // lot_step) * lot_step
        
        # Calculate fees
        entry_fees = self.calculate_fees(symbol, final_size, entry_price, is_maker_order)
        exit_fees = self.calculate_fees(symbol, final_size, entry_price, False)  # Assume market exit
        
        # Final validation
        if final_size <= 0:
            return EnhancedAssessment(
                accept=False,
                reason="Computed size too small after adjustments",
                max_size_units=0.0,
                heat_after=used_heat / max(equity, 1e-9),
                concurrency_after=len(self.open_positions),
                dynamic_risk_used=risk_per_trade_fraction
            )
        
        # Calculate projected heat
        projected_risk = self._per_trade_risk_quote(entry_price, stop_price, final_size, side)
        projected_heat = used_heat + projected_risk + entry_fees + exit_fees
        
        return EnhancedAssessment(
            accept=True,
            reason="Approved",
            max_size_units=float(final_size),
            heat_after=projected_heat / max(equity, 1e-9),
            concurrency_after=len(self.open_positions) + 1,
            dynamic_risk_used=risk_per_trade_fraction,
            volatility_multiplier=volatility_mult,
            entry_fees=entry_fees,
            expected_exit_fees=exit_fees
        )
    
    def register_enhanced_entry(self, 
                               symbol: str, 
                               entry_price: float, 
                               stop_price: float, 
                               size_units: float, 
                               opened_at: datetime, 
                               tag: str = "",
                               atr: float = 0.0,
                               correlation: float = 0.0,
                               side: str = "long",
                               actual_entry_fees: float = 0.0):
        """Register enhanced position entry"""
        
        expected_exit_fees = self.calculate_fees(symbol, size_units, entry_price, False)
        
        position = EnhancedPosition(
            symbol=symbol,
            entry_price=entry_price,
            stop_price=stop_price,
            size_units=size_units,
            opened_at=opened_at,
            tag=tag,
            side=side,
            entry_fees=actual_entry_fees,
            atr_at_entry=atr,
            correlation_at_entry=correlation,
            expected_exit_fees=expected_exit_fees
        )
        
        position.per_trade_risk_quote = self._per_trade_risk_quote(
            entry_price, stop_price, size_units, side
        )
        
        self.open_positions[symbol] = position
        self._save()
        
        logger.info(f"Enhanced position registered: {symbol} {side} {size_units:.6f} @ {entry_price:.4f}")
    
    def register_enhanced_exit(self, 
                              symbol: str, 
                              exit_price: float,
                              exit_size: float,
                              realized_pnl_quote: float, 
                              closed_at: datetime,
                              actual_exit_fees: float = 0.0):
        """Register enhanced position exit with performance tracking"""
        
        if symbol in self.open_positions:
            position = self.open_positions[symbol]
            
            # Update performance metrics
            self.performance_metrics.total_trades += 1
            
            # Calculate fee-adjusted PnL
            fee_adjusted_pnl = realized_pnl_quote - actual_exit_fees
            
            if fee_adjusted_pnl > 0:
                self.performance_metrics.winning_trades += 1
                self.performance_metrics.current_win_streak += 1
                self.performance_metrics.current_loss_streak = 0
                self.performance_metrics.max_consecutive_wins = max(
                    self.performance_metrics.max_consecutive_wins,
                    self.performance_metrics.current_win_streak
                )
            else:
                self.performance_metrics.losing_trades += 1
                self.performance_metrics.current_loss_streak += 1
                self.performance_metrics.current_win_streak = 0
                self.performance_metrics.max_consecutive_losses = max(
                    self.performance_metrics.max_consecutive_losses,
                    self.performance_metrics.current_loss_streak
                )
            
            self.performance_metrics.total_pnl += fee_adjusted_pnl
            
            # Remove or reduce position
            if exit_size >= position.size_units:
                del self.open_positions[symbol]
            else:
                position.size_units -= exit_size
                position.per_trade_risk_quote = self._per_trade_risk_quote(
                    position.entry_price, position.stop_price, position.size_units, position.side
                )
        
        self.realized_pnl_today += realized_pnl_quote
        self._save()
        
        logger.info(f"Enhanced exit registered: {symbol} PnL={realized_pnl_quote:.2f} (fee-adj: {realized_pnl_quote - actual_exit_fees:.2f})")
    
    def update_stop(self, symbol: str, new_stop_price: float):
        """Update stop with enhanced tracking"""
        if symbol in self.open_positions:
            position = self.open_positions[symbol]
            position.stop_price = float(new_stop_price)
            position.per_trade_risk_quote = self._per_trade_risk_quote(
                position.entry_price, position.stop_price, position.size_units, position.side
            )
            self._save()
    
    def update_size(self, symbol: str, new_size_units: float):
        """Update size with enhanced tracking"""
        if symbol in self.open_positions:
            position = self.open_positions[symbol]
            position.size_units = float(new_size_units)
            position.per_trade_risk_quote = self._per_trade_risk_quote(
                position.entry_price, position.stop_price, position.size_units, position.side
            )
            self._save()
    
    def can_trade(self) -> Tuple[bool, str]:
        """Enhanced trading gate check"""
        if not self.trading_enabled:
            return False, "Risk gates disabled trading"
        
        if len(self.open_positions) >= self.max_concurrent:
            return False, "Max concurrency reached"
        
        # Additional checks based on performance
        if (self.performance_metrics.current_loss_streak >= 
            self.dynamic_config.max_consecutive_losses_before_reduction * 2):
            return False, f"Excessive loss streak: {self.performance_metrics.current_loss_streak}"
        
        return True, "OK"
    
    def get_risk_level(self) -> RiskLevel:
        """Determine current risk level based on performance"""
        win_rate = self.performance_metrics.win_rate()
        profit_factor = self.performance_metrics.profit_factor()
        
        if (win_rate >= 70 and profit_factor >= 2.0 and 
            self.performance_metrics.current_win_streak >= 3):
            return RiskLevel.MAXIMUM
        elif (win_rate >= 60 and profit_factor >= 1.5):
            return RiskLevel.AGGRESSIVE
        elif (win_rate >= 45 and profit_factor >= 1.2):
            return RiskLevel.NORMAL
        else:
            return RiskLevel.CONSERVATIVE
    
    def get_performance_summary(self) -> Dict:
        """Get comprehensive performance summary"""
        return {
            "risk_level": self.get_risk_level().value,
            "total_trades": self.performance_metrics.total_trades,
            "win_rate": self.performance_metrics.win_rate(),
            "profit_factor": self.performance_metrics.profit_factor(),
            "total_pnl": self.performance_metrics.total_pnl,
            "current_win_streak": self.performance_metrics.current_win_streak,
            "current_loss_streak": self.performance_metrics.current_loss_streak,
            "sharpe_ratio": self.performance_metrics.sharpe_ratio,
            "max_drawdown_pct": self.performance_metrics.max_drawdown_pct,
            "open_positions": len(self.open_positions),
            "portfolio_heat": f"{self.current_portfolio_heat():.2%}",
            "trading_enabled": self.trading_enabled
        }

@dataclass
class EnhancedAssessment:
    """Enhanced assessment result with additional metrics"""
    accept: bool
    reason: str
    max_size_units: float
    heat_after: float
    concurrency_after: int
    dynamic_risk_used: float
    volatility_multiplier: float = 1.0
    entry_fees: float = 0.0
    expected_exit_fees: float = 0.0