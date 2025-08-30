from dataclasses import dataclass
from typing import Optional

@dataclass
class CircuitBreaker:
    max_daily_loss: float  # percent
    max_drawdown: float  # percent
    max_consecutive_losses: int
    
    equity_high_water: float
    equity_start_day: float
    losses_today: int = 0
    day_loss_pct: float = 0.0
    drawdown_pct: float = 0.0
    tripped: bool = False
    reason: Optional[str] = None

    def on_trade_close(self, pnl: float, equity: float):
        if pnl < 0:
            self.losses_today += 1
        
        self.equity_high_water = max(self.equity_high_water, equity)
        self.drawdown_pct = 100.0 * (self.equity_high_water - equity) / max(1e-9, self.equity_high_water)
        self.day_loss_pct = 100.0 * (self.equity_start_day - equity) / max(1e-9, self.equity_start_day)
        
        if self.day_loss_pct >= self.max_daily_loss:
            self.tripped, self.reason = True, 'max_daily_loss'
        if self.drawdown_pct >= self.max_drawdown:
            self.tripped, self.reason = True, 'max_drawdown'
        if self.losses_today >= self.max_consecutive_losses:
            self.tripped, self.reason = True, 'consecutive_losses'

    def reset_day(self, equity: float):
        self.equity_start_day = equity
        self.losses_today = 0
        self.day_loss_pct = 0.0