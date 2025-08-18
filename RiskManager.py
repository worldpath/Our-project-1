
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date
import json

@dataclass
class Position:
    symbol: str
    entry_price: float
    stop_price: float
    size_units: float
    opened_at: datetime
    tag: str = ""
    per_trade_risk_quote: float = 0.0

@dataclass
class Assessment:
    accept: bool
    reason: str
    max_size_units: float
    heat_after: float
    concurrency_after: int

@dataclass
class RiskManager:
    max_portfolio_heat: float = 0.10
    max_daily_loss: float = 0.05
    max_drawdown: float = 0.25
    max_concurrent: int = 3
    correlation_gate: bool = True
    corr_threshold: float = 0.60
    state_path: str = "risk_state.json"

    open_positions: Dict[str, Position] = field(default_factory=dict)
    equity_peak: float = 0.0
    today: Optional[date] = None
    start_of_day_equity: float = 0.0
    realized_pnl_today: float = 0.0
    trading_enabled: bool = True

    def _save(self):
        s = {
            "equity_peak": self.equity_peak,
            "today": self.today.isoformat() if self.today else None,
            "start_of_day_equity": self.start_of_day_equity,
            "realized_pnl_today": self.realized_pnl_today,
            "trading_enabled": self.trading_enabled,
            "open_positions": {
                sym: {
                    "entry_price": p.entry_price,
                    "stop_price": p.stop_price,
                    "size_units": p.size_units,
                    "opened_at": p.opened_at.isoformat(),
                    "tag": p.tag,
                    "per_trade_risk_quote": p.per_trade_risk_quote,
                } for sym,p in self.open_positions.items()
            }
        }
        try:
            with open(self.state_path, "w") as f:
                json.dump(s, f, indent=2)
        except Exception:
            pass

    def _load(self):
        try:
            with open(self.state_path, "r") as f:
                s = json.load(f)
            self.equity_peak = s.get("equity_peak",0.0)
            self.today = date.fromisoformat(s["today"]) if s.get("today") else None
            self.start_of_day_equity = s.get("start_of_day_equity",0.0)
            self.realized_pnl_today = s.get("realized_pnl_today",0.0)
            self.trading_enabled = s.get("trading_enabled",True)
            self.open_positions = {}
            for sym,p in s.get("open_positions",{}).items():
                self.open_positions[sym] = Position(
                    sym, p["entry_price"], p["stop_price"], p["size_units"],
                    datetime.fromisoformat(p["opened_at"]), p.get("tag",""),
                    p.get("per_trade_risk_quote",0.0)
                )
        except Exception:
            pass

    def on_start(self): self._load()
    def flush(self): self._save()

    def on_bar_start(self, now: datetime, equity: float):
        if self.today != now.date():
            self.today = now.date()
            self.start_of_day_equity = equity
            self.realized_pnl_today = 0.0
            self.trading_enabled = True
            self._save()
        if equity > self.equity_peak:
            self.equity_peak = equity; self._save()
        if self.equity_peak>0 and (self.equity_peak - equity)/self.equity_peak >= self.max_drawdown:
            self.trading_enabled = False
        if self.start_of_day_equity>0 and (self.start_of_day_equity - equity)/self.start_of_day_equity >= self.max_daily_loss:
            self.trading_enabled = False

    def current_portfolio_heat(self) -> float:
        return sum(p.per_trade_risk_quote for p in self.open_positions.values())

    def _per_trade_risk_quote(self, entry: float, stop: float, size: float) -> float:
        if stop >= entry: return 0.0
        return max(0.0, (entry - stop) * size)

    def assess_new_position(self, symbol: str, entry_price: float, stop_price: float, equity: float, risk_per_trade_fraction: float, lot_step: float=0.000001, avg_pairwise_corr: float=None) -> Assessment:
        if not self.trading_enabled:
            return Assessment(False, "Trading disabled by gates", 0.0, self.current_portfolio_heat()/max(equity,1e-9), len(self.open_positions))
        if len(self.open_positions) >= self.max_concurrent:
            return Assessment(False, f"Max concurrency {self.max_concurrent} reached", 0.0, self.current_portfolio_heat()/max(equity,1e-9), len(self.open_positions))
        if self.correlation_gate and avg_pairwise_corr is not None and avg_pairwise_corr >= self.corr_threshold:
            return Assessment(False, f"Correlation {avg_pairwise_corr:.2f} >= {self.corr_threshold:.2f}", 0.0, self.current_portfolio_heat()/max(equity,1e-9), len(self.open_positions))
        used = self.current_portfolio_heat(); headroom = max(0.0, self.max_portfolio_heat*equity - used)
        rpu = entry_price - stop_price
        if rpu <= 0: return Assessment(False, "Invalid stop", 0.0, used/max(equity,1e-9), len(self.open_positions))
        desired = equity*risk_per_trade_fraction / rpu
        by_heat = headroom / rpu if rpu>0 else 0.0
        size = max(0.0, min(desired, by_heat))
        if lot_step>0: size = (size // lot_step) * lot_step
        proj_heat = used + self._per_trade_risk_quote(entry_price, stop_price, size)
        if size<=0: return Assessment(False, "Computed size too small", 0.0, proj_heat/max(equity,1e-9), len(self.open_positions))
        return Assessment(True, "Approved", float(size), proj_heat/max(equity,1e-9), len(self.open_positions)+1)

    def register_entry(self, symbol: str, entry_price: float, stop_price: float, size_units: float, opened_at: datetime, tag: str=""):
        p = Position(symbol, entry_price, stop_price, size_units, opened_at, tag)
        p.per_trade_risk_quote = self._per_trade_risk_quote(p.entry_price, p.stop_price, p.size_units)
        self.open_positions[symbol] = p; self._save()

    def update_stop(self, symbol: str, new_stop_price: float):
        if symbol in self.open_positions:
            p = self.open_positions[symbol]; p.stop_price = float(new_stop_price)
            p.per_trade_risk_quote = self._per_trade_risk_quote(p.entry_price, p.stop_price, p.size_units); self._save()

    def update_size(self, symbol: str, new_size_units: float):
        if symbol in self.open_positions:
            p = self.open_positions[symbol]; p.size_units = float(new_size_units)
            p.per_trade_risk_quote = self._per_trade_risk_quote(p.entry_price, p.stop_price, p.size_units); self._save()

    def register_exit(self, symbol: str, realized_pnl_quote: float, closed_at: datetime):
        if symbol in self.open_positions: del self.open_positions[symbol]
        self.realized_pnl_today += realized_pnl_quote; self._save()

    def can_trade(self): 
        if not self.trading_enabled: return False, "Risk gates disabled trading"
        if len(self.open_positions) >= self.max_concurrent: return False, "Max concurrency reached"
        return True, "OK"
