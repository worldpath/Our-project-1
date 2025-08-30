from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal, Tuple
from datetime import datetime, timezone, timedelta
import csv

Basis = Literal['FIFO','HIFO','LIFO','SPECIFIC']

@dataclass
class Lot:
    id: str
    asset: str
    qty: float
    cost_per_unit_usd: float
    acquired: datetime

@dataclass 
class Realization:
    asset: str
    qty: float
    proceeds_usd: float
    basis_usd: float
    gain_usd: float
    short_term: bool
    opened: datetime
    closed: datetime
    lot_ids: List[str]

class Ledger:
    def __init__(self):
        self.lots: Dict[str, List[Lot]] = {}
        self.realized: List[Realization] = []

    def add_buy(self, asset: str, qty: float, total_cost_usd: float, ts: Optional[datetime] = None, lot_id: Optional[str] = None):
        ts = ts or datetime.now(timezone.utc)
        lot = Lot(id=lot_id or f"{asset}-{ts.timestamp()}", asset=asset, qty=qty, cost_per_unit_usd=total_cost_usd/max(1e-9,qty), acquired=ts)
        self.lots.setdefault(asset, []).append(lot)

    def _order_lots(self, asset: str, basis: Basis) -> List[Lot]:
        lots = list(self.lots.get(asset, []))
        if basis == 'FIFO':
            lots.sort(key=lambda l: l.acquired)  # oldest first
        elif basis == 'LIFO':
            lots.sort(key=lambda l: l.acquired, reverse=True)
        elif basis == 'HIFO':
            lots.sort(key=lambda l: l.cost_per_unit_usd, reverse=True)
        return lots

    def sell(self, asset: str, qty: float, proceeds_usd: float, ts: Optional[datetime] = None, basis: Basis = 'HIFO', specific_ids: Optional[List[str]] = None):
        ts = ts or datetime.now(timezone.utc)
        remaining = qty
        chosen: List[Lot] = []
        
        if basis == 'SPECIFIC' and specific_ids:
            idset = set(specific_ids)
            pool = [l for l in self.lots.get(asset, []) if l.id in idset]
            if sum(l.qty for l in pool) + 1e-9 < qty:
                raise ValueError('Not enough quantity in specified lots')
            # Preserve given order
            for lid in specific_ids:
                for l in self.lots.get(asset, []):
                    if l.id == lid and l.qty > 0:
                        chosen.append(l)
        else:
            chosen = self._order_lots(asset, basis)

        consumed: List[Tuple[Lot, float]] = []
        for lot in chosen:
            if remaining <= 0:
                break
            take = min(remaining, lot.qty)
            if take > 0:
                consumed.append((lot, take))
                lot.qty -= take
                remaining -= take

        if remaining > 1e-12:
            raise ValueError('Insufficient quantity to sell')

        # Weighted average cost for the consumed pieces
        basis_usd = sum(take * lot.cost_per_unit_usd for lot, take in consumed)
        gain_usd = proceeds_usd - basis_usd
        opened = min(lot.acquired for lot, _ in consumed)
        short_term = (ts - opened) < timedelta(days=365)
        
        self.realized.append(Realization(
            asset=asset, qty=qty, proceeds_usd=proceeds_usd, basis_usd=basis_usd, gain_usd=gain_usd,
            short_term=short_term, opened=opened, closed=ts, lot_ids=[lot.id for lot,_ in consumed]
        ))

    def export_8949_csv(self, path: str):
        with open(path, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['Description','Date Acquired','Date Sold','Proceeds','Cost or Other Basis','Adjustment','Gain or (Loss)','Short/Long','Lot IDs'])
            for r in self.realized:
                w.writerow([
                    f"{r.asset} sale",
                    r.opened.strftime('%m/%d/%Y'),
                    r.closed.strftime('%m/%d/%Y'), 
                    f"{r.proceeds_usd:.2f}",
                    f"{r.basis_usd:.2f}",
                    "0.00",
                    f"{r.gain_usd:.2f}",
                    "Short-term" if r.short_term else "Long-term",
                    "|".join(r.lot_ids)
                ])