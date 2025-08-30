from dataclasses import dataclass
from typing import Optional

@dataclass
class LiquidityRules:
    min_usd_volume_24h: float = 5_000_000.0  # default for US venues
    max_spread_bps: float = 25.0  # 25 bps = 0.25%
    top_n: int = 30  # cap symbol universe

def is_tradeable(volume_24h_usd: float, best_bid: float, best_ask: float, rules: LiquidityRules) -> bool:
    if best_bid <= 0 or best_ask <= 0:
        return False
    spread_bps = (best_ask - best_bid) / ((best_ask + best_bid) / 2.0) * 10_000
    return volume_24h_usd >= rules.min_usd_volume_24h and spread_bps <= rules.max_spread_bps