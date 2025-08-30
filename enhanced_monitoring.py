"""
Enhanced Monitoring System with Prometheus Integration
====================================================

Features:
- Real-time PNL threshold alerts
- Prometheus metrics collection
- Advanced performance dashboard
- System health monitoring
- Trading signal metrics
- Risk metrics tracking
"""

import time
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
import json
from pathlib import Path

try:
    from prometheus_client import (
        Counter, Gauge, Histogram, CollectorRegistry, 
        generate_latest, CONTENT_TYPE_LATEST, start_http_server
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    print("⚠️ Prometheus client not available. Install with: pip install prometheus-client")

logger = logging.getLogger(__name__)

@dataclass
class AlertConfig:
    """Configuration for PNL and system alerts"""
    # PnL alert thresholds (as percentages)
    daily_loss_alert: float = -0.05  # -5%
    daily_loss_critical: float = -0.10  # -10%
    drawdown_warning: float = -0.15  # -15%
    drawdown_critical: float = -0.25  # -25%
    
    # Performance alerts
    win_rate_warning: float = 40.0  # Below 40%
    profit_factor_warning: float = 1.2  # Below 1.2
    consecutive_losses_alert: int = 3
    consecutive_losses_critical: int = 5
    
    # System health alerts
    api_latency_warning: float = 1000.0  # 1 second
    memory_usage_warning: float = 0.8  # 80%
    disk_usage_warning: float = 0.9  # 90%
    
    # Alert cooldown (seconds)
    alert_cooldown: int = 300  # 5 minutes

class PrometheusMetrics:
    """Prometheus metrics collector for trading bot"""
    
    def __init__(self, port: int = 8000):
        if not PROMETHEUS_AVAILABLE:
            logger.warning("Prometheus metrics disabled - prometheus_client not installed")
            return
            
        self.registry = CollectorRegistry()
        self.port = port
        
        # Trading metrics
        self.trades_total = Counter(
            'crypto_bot_trades_total',
            'Total number of trades executed',
            ['symbol', 'side', 'strategy', 'outcome'],
            registry=self.registry
        )
        
        self.pnl_realized = Gauge(
            'crypto_bot_pnl_realized_total',
            'Total realized PnL',
            registry=self.registry
        )
        
        self.pnl_unrealized = Gauge(
            'crypto_bot_pnl_unrealized_total', 
            'Total unrealized PnL',
            registry=self.registry
        )
        
        self.equity_value = Gauge(
            'crypto_bot_equity_value',
            'Current equity value',
            registry=self.registry
        )
        
        self.portfolio_heat = Gauge(
            'crypto_bot_portfolio_heat',
            'Portfolio heat (risk exposure)',
            registry=self.registry
        )
        
        self.open_positions = Gauge(
            'crypto_bot_open_positions',
            'Number of open positions',
            ['symbol'],
            registry=self.registry
        )
        
        # Performance metrics
        self.win_rate = Gauge(
            'crypto_bot_win_rate',
            'Current win rate percentage',
            registry=self.registry
        )
        
        self.profit_factor = Gauge(
            'crypto_bot_profit_factor',
            'Current profit factor',
            registry=self.registry
        )
        
        self.sharpe_ratio = Gauge(
            'crypto_bot_sharpe_ratio',
            'Sharpe ratio',
            registry=self.registry
        )
        
        self.max_drawdown = Gauge(
            'crypto_bot_max_drawdown',
            'Maximum drawdown percentage',
            registry=self.registry
        )
        
        # Signal metrics
        self.signals_generated = Counter(
            'crypto_bot_signals_generated_total',
            'Total signals generated',
            ['symbol', 'strategy', 'signal_type'],
            registry=self.registry
        )
        
        self.signals_executed = Counter(
            'crypto_bot_signals_executed_total',
            'Total signals executed',
            ['symbol', 'strategy', 'signal_type'],
            registry=self.registry
        )
        
        # Risk metrics
        self.risk_per_trade = Gauge(
            'crypto_bot_risk_per_trade',
            'Current dynamic risk per trade',
            registry=self.registry
        )
        
        self.correlation_average = Gauge(
            'crypto_bot_correlation_average',
            'Average pairwise correlation',
            registry=self.registry
        )
        
        # System metrics
        self.api_latency = Histogram(
            'crypto_bot_api_latency_seconds',
            'API call latency',
            ['endpoint'],
            registry=self.registry
        )
        
        self.system_health = Gauge(
            'crypto_bot_system_health',
            'System health score (0-1)',
            registry=self.registry
        )
        
        # Trading session metrics
        self.trading_enabled = Gauge(
            'crypto_bot_trading_enabled',
            'Trading enabled status (1=enabled, 0=disabled)',
            registry=self.registry
        )
        
        # Start metrics server
        self._start_server()
    
    def _start_server(self):
        """Start Prometheus metrics HTTP server"""
        try:
            start_http_server(self.port, registry=self.registry)
            logger.info(f"✅ Prometheus metrics server started on port {self.port}")
        except Exception as e:
            logger.error(f"❌ Failed to start Prometheus server: {e}")
    
    def record_trade(self, symbol: str, side: str, strategy: str, outcome: str):
        """Record a completed trade"""
        if PROMETHEUS_AVAILABLE:
            self.trades_total.labels(symbol=symbol, side=side, strategy=strategy, outcome=outcome).inc()
    
    def update_pnl(self, realized_pnl: float, unrealized_pnl: float):
        """Update PnL metrics"""
        if PROMETHEUS_AVAILABLE:
            self.pnl_realized.set(realized_pnl)
            self.pnl_unrealized.set(unrealized_pnl)
    
    def update_portfolio_metrics(self, equity: float, heat: float, num_positions: int):
        """Update portfolio metrics"""
        if PROMETHEUS_AVAILABLE:
            self.equity_value.set(equity)
            self.portfolio_heat.set(heat)
            # Clear previous position counts
            self.open_positions.clear()
    
    def update_position_count(self, symbol: str, count: int):
        """Update position count for specific symbol"""
        if PROMETHEUS_AVAILABLE:
            self.open_positions.labels(symbol=symbol).set(count)
    
    def update_performance_metrics(self, win_rate: float, profit_factor: float, 
                                 sharpe: float, max_dd: float):
        """Update performance metrics"""
        if PROMETHEUS_AVAILABLE:
            self.win_rate.set(win_rate)
            self.profit_factor.set(profit_factor)
            self.sharpe_ratio.set(sharpe)
            self.max_drawdown.set(max_dd)
    
    def record_signal(self, symbol: str, strategy: str, signal_type: str, executed: bool = False):
        """Record signal generation/execution"""
        if PROMETHEUS_AVAILABLE:
            self.signals_generated.labels(symbol=symbol, strategy=strategy, signal_type=signal_type).inc()
            if executed:
                self.signals_executed.labels(symbol=symbol, strategy=strategy, signal_type=signal_type).inc()
    
    def update_risk_metrics(self, risk_per_trade: float, correlation: float):
        """Update risk metrics"""
        if PROMETHEUS_AVAILABLE:
            self.risk_per_trade.set(risk_per_trade)
            self.correlation_average.set(correlation)
    
    def record_api_latency(self, endpoint: str, latency_seconds: float):
        """Record API call latency"""
        if PROMETHEUS_AVAILABLE:
            self.api_latency.labels(endpoint=endpoint).observe(latency_seconds)
    
    def update_system_health(self, health_score: float, trading_enabled: bool):
        """Update system health metrics"""
        if PROMETHEUS_AVAILABLE:
            self.system_health.set(health_score)
            self.trading_enabled.set(1.0 if trading_enabled else 0.0)

@dataclass
class AlertState:
    """Track alert states to prevent spam"""
    last_alert_times: Dict[str, datetime] = field(default_factory=dict)
    alert_counts: Dict[str, int] = field(default_factory=dict)

class EnhancedMonitor:
    """Enhanced monitoring system with alerts and Prometheus integration"""
    
    def __init__(self, 
                 alert_config: AlertConfig = AlertConfig(),
                 prometheus_port: int = 8000,
                 alert_callbacks: List[Callable[[str, str], None]] = None):
        
        self.alert_config = alert_config
        self.alert_state = AlertState()
        self.alert_callbacks = alert_callbacks or []
        
        # Initialize Prometheus metrics
        self.metrics = PrometheusMetrics(prometheus_port) if PROMETHEUS_AVAILABLE else None
        
        # Monitoring state
        self.last_equity = 0.0
        self.daily_start_equity = 0.0
        self.monitoring_active = False
        
        logger.info("✅ Enhanced monitoring system initialized")
    
    def add_alert_callback(self, callback: Callable[[str, str], None]):
        """Add callback for alerts (level, message)"""
        self.alert_callbacks.append(callback)
    
    def _send_alert(self, level: str, message: str, alert_key: str = None):
        """Send alert with cooldown logic"""
        
        if alert_key:
            current_time = datetime.now()
            last_alert = self.alert_state.last_alert_times.get(alert_key)
            
            if last_alert and (current_time - last_alert).seconds < self.alert_config.alert_cooldown:
                return  # Skip due to cooldown
            
            self.alert_state.last_alert_times[alert_key] = current_time
            self.alert_state.alert_counts[alert_key] = self.alert_state.alert_counts.get(alert_key, 0) + 1
        
        # Send to all configured callbacks
        for callback in self.alert_callbacks:
            try:
                callback(level, message)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
        
        # Log alert
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(f"ALERT [{level}]: {message}")
    
    def check_pnl_alerts(self, current_equity: float, daily_start_equity: float):
        """Check for PnL-based alerts"""
        
        if daily_start_equity <= 0:
            return
        
        daily_pnl_pct = (current_equity - daily_start_equity) / daily_start_equity
        
        # Daily loss alerts
        if daily_pnl_pct <= self.alert_config.daily_loss_critical:
            self._send_alert(
                "CRITICAL",
                f"🚨 CRITICAL DAILY LOSS: {daily_pnl_pct:.2%} (Threshold: {self.alert_config.daily_loss_critical:.2%})",
                "daily_loss_critical"
            )
        elif daily_pnl_pct <= self.alert_config.daily_loss_alert:
            self._send_alert(
                "WARNING", 
                f"⚠️ Daily Loss Alert: {daily_pnl_pct:.2%}",
                "daily_loss_warning"
            )
        
        # Drawdown alerts (if we have equity peak)
        if self.last_equity > 0:
            equity_peak = max(self.last_equity, current_equity)
            drawdown_pct = (equity_peak - current_equity) / equity_peak
            
            if drawdown_pct >= abs(self.alert_config.drawdown_critical):
                self._send_alert(
                    "CRITICAL",
                    f"🚨 CRITICAL DRAWDOWN: {drawdown_pct:.2%}",
                    "drawdown_critical"
                )
            elif drawdown_pct >= abs(self.alert_config.drawdown_warning):
                self._send_alert(
                    "WARNING",
                    f"⚠️ Drawdown Warning: {drawdown_pct:.2%}",
                    "drawdown_warning"
                )
    
    def check_performance_alerts(self, performance_metrics: Dict):
        """Check for performance-based alerts"""
        
        win_rate = performance_metrics.get('win_rate', 0)
        profit_factor = performance_metrics.get('profit_factor', 0)
        consecutive_losses = performance_metrics.get('current_loss_streak', 0)
        
        # Win rate alerts
        if win_rate < self.alert_config.win_rate_warning:
            self._send_alert(
                "WARNING",
                f"⚠️ Low Win Rate: {win_rate:.1f}% (Threshold: {self.alert_config.win_rate_warning:.1f}%)",
                "low_win_rate"
            )
        
        # Profit factor alerts
        if profit_factor < self.alert_config.profit_factor_warning:
            self._send_alert(
                "WARNING",
                f"⚠️ Low Profit Factor: {profit_factor:.2f} (Threshold: {self.alert_config.profit_factor_warning:.2f})",
                "low_profit_factor"
            )
        
        # Consecutive losses
        if consecutive_losses >= self.alert_config.consecutive_losses_critical:
            self._send_alert(
                "CRITICAL",
                f"🚨 CRITICAL: {consecutive_losses} Consecutive Losses!",
                "consecutive_losses_critical"
            )
        elif consecutive_losses >= self.alert_config.consecutive_losses_alert:
            self._send_alert(
                "WARNING",
                f"⚠️ {consecutive_losses} Consecutive Losses",
                "consecutive_losses_warning"
            )
    
    def update_trading_metrics(self, 
                             equity: float,
                             daily_start_equity: float, 
                             portfolio_heat: float,
                             performance_metrics: Dict,
                             open_positions: Dict,
                             trading_enabled: bool):
        """Update all trading metrics and check alerts"""
        
        # Update Prometheus metrics
        if self.metrics:
            realized_pnl = performance_metrics.get('total_pnl', 0)
            unrealized_pnl = sum(pos.get('unrealized_pnl', 0) for pos in open_positions.values())
            
            self.metrics.update_pnl(realized_pnl, unrealized_pnl)
            self.metrics.update_portfolio_metrics(equity, portfolio_heat, len(open_positions))
            
            # Update position counts by symbol
            for symbol in open_positions:
                self.metrics.update_position_count(symbol, 1)
            
            # Update performance metrics
            self.metrics.update_performance_metrics(
                performance_metrics.get('win_rate', 0),
                performance_metrics.get('profit_factor', 0),
                performance_metrics.get('sharpe_ratio', 0),
                performance_metrics.get('max_drawdown_pct', 0)
            )
            
            # System health (simplified calculation)
            health_score = min(1.0, max(0.0, 
                (performance_metrics.get('win_rate', 0) / 100) * 0.5 +
                (min(performance_metrics.get('profit_factor', 0), 3.0) / 3.0) * 0.5
            ))
            
            self.metrics.update_system_health(health_score, trading_enabled)
        
        # Check alerts
        self.check_pnl_alerts(equity, daily_start_equity)
        self.check_performance_alerts(performance_metrics)
        
        # Update state
        self.last_equity = equity
        self.daily_start_equity = daily_start_equity
    
    def record_trade_execution(self, symbol: str, side: str, strategy: str, 
                             pnl: float, fees: float):
        """Record trade execution with outcome"""
        if self.metrics:
            outcome = "win" if pnl > 0 else "loss"
            self.metrics.record_trade(symbol, side, strategy, outcome)
        
        # Log significant trades
        if abs(pnl) > 100:  # Significant PnL threshold
            level = "INFO" if pnl > 0 else "WARNING"
            self._send_alert(
                level,
                f"Trade completed: {symbol} {side} PnL=${pnl:.2f} Fees=${fees:.2f}",
                f"large_trade_{symbol}"
            )
    
    def record_signal_generation(self, symbol: str, strategy: str, signal_type: str, 
                               executed: bool = False):
        """Record signal generation and execution"""
        if self.metrics:
            self.metrics.record_signal(symbol, strategy, signal_type, executed)
    
    def record_api_call(self, endpoint: str, duration_seconds: float):
        """Record API call metrics"""
        if self.metrics:
            self.metrics.record_api_latency(endpoint, duration_seconds)
        
        # Alert on high latency
        if duration_seconds > self.alert_config.api_latency_warning / 1000:
            self._send_alert(
                "WARNING",
                f"⚠️ High API Latency: {endpoint} took {duration_seconds:.2f}s",
                f"api_latency_{endpoint}"
            )
    
    def update_risk_metrics(self, risk_per_trade: float, correlation: float):
        """Update risk-related metrics"""
        if self.metrics:
            self.metrics.update_risk_metrics(risk_per_trade, correlation)
        
        # Alert on high correlation
        if correlation > 0.8:
            self._send_alert(
                "WARNING",
                f"⚠️ High Correlation: {correlation:.2f}",
                "high_correlation"
            )
    
    def get_metrics_export(self) -> str:
        """Get Prometheus metrics in text format"""
        if self.metrics and PROMETHEUS_AVAILABLE:
            return generate_latest(self.metrics.registry).decode('utf-8')
        return "# Prometheus metrics not available\n"
    
    def generate_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "monitoring_active": self.monitoring_active,
            "alerts_sent_today": sum(1 for t in self.alert_state.last_alert_times.values() 
                                   if t.date() == datetime.now().date()),
            "prometheus_enabled": PROMETHEUS_AVAILABLE,
            "metrics_endpoint": f"http://localhost:{self.metrics.port}/metrics" if self.metrics else None,
            "last_equity": self.last_equity,
            "system_status": "healthy" if self.monitoring_active else "inactive"
        }
        
        return report

# ============================================================================
# ENHANCED NOTIFICATION SYSTEM
# ============================================================================

class NotificationManager:
    """Centralized notification management"""
    
    def __init__(self):
        self.handlers = []
        self.rate_limits = {}
    
    def add_handler(self, handler: Callable[[str, str], None]):
        """Add notification handler (level, message) -> None"""
        self.handlers.append(handler)
    
    def send_notification(self, level: str, message: str, rate_limit_key: str = None):
        """Send notification through all handlers"""
        
        # Simple rate limiting
        if rate_limit_key:
            last_sent = self.rate_limits.get(rate_limit_key, 0)
            if time.time() - last_sent < 300:  # 5 minute rate limit
                return
            self.rate_limits[rate_limit_key] = time.time()
        
        for handler in self.handlers:
            try:
                handler(level, message)
            except Exception as e:
                logger.error(f"Notification handler failed: {e}")

# ============================================================================
# EMAIL NOTIFICATION HANDLER
# ============================================================================

def create_email_handler(smtp_config: Dict[str, str]) -> Callable[[str, str], None]:
    """Create email notification handler"""
    
    def send_email_alert(level: str, message: str):
        try:
            from notifier import notify_email
            subject = f"Crypto Bot Alert [{level}]"
            notify_email(subject, message)
        except Exception as e:
            logger.error(f"Email notification failed: {e}")
    
    return send_email_alert

# ============================================================================
# TELEGRAM NOTIFICATION HANDLER  
# ============================================================================

def create_telegram_handler(bot_token: str, chat_id: str) -> Callable[[str, str], None]:
    """Create Telegram notification handler"""
    
    def send_telegram_alert(level: str, message: str):
        try:
            from notifier import notify_telegram
            formatted_message = f"🤖 *Crypto Bot Alert* [{level}]\n\n{message}"
            notify_telegram(formatted_message)
        except Exception as e:
            logger.error(f"Telegram notification failed: {e}")
    
    return send_telegram_alert

# ============================================================================
# USAGE EXAMPLE
# ============================================================================

def setup_enhanced_monitoring(prometheus_port: int = 8000) -> EnhancedMonitor:
    """Setup enhanced monitoring with default configuration"""
    
    # Create alert configuration
    alert_config = AlertConfig(
        daily_loss_alert=-0.05,      # -5% daily loss warning
        daily_loss_critical=-0.10,   # -10% daily loss critical
        drawdown_warning=-0.15,      # -15% drawdown warning
        consecutive_losses_alert=3,   # 3 consecutive losses warning
    )
    
    # Initialize monitor
    monitor = EnhancedMonitor(
        alert_config=alert_config,
        prometheus_port=prometheus_port
    )
    
    # Setup notification handlers
    try:
        # Email handler
        email_handler = create_email_handler({})
        monitor.add_alert_callback(email_handler)
        
        # Telegram handler  
        telegram_handler = create_telegram_handler("", "")
        monitor.add_alert_callback(telegram_handler)
        
        logger.info("✅ Enhanced monitoring configured with email and Telegram alerts")
        
    except Exception as e:
        logger.warning(f"⚠️ Some notification handlers failed to initialize: {e}")
    
    return monitor

if __name__ == "__main__":
    # Example usage
    monitor = setup_enhanced_monitoring()
    
    # Simulate some metrics updates
    monitor.update_trading_metrics(
        equity=10000,
        daily_start_equity=10500,  # -5% daily loss
        portfolio_heat=0.08,
        performance_metrics={
            'win_rate': 35.0,  # Low win rate
            'profit_factor': 1.1,  # Low profit factor
            'total_pnl': -500,
            'current_loss_streak': 4,  # High loss streak
            'sharpe_ratio': 0.8,
            'max_drawdown_pct': 0.20
        },
        open_positions={'BTC/USDT': {}, 'ETH/USDT': {}},
        trading_enabled=True
    )
    
    print("Monitor health report:")
    print(json.dumps(monitor.generate_health_report(), indent=2))