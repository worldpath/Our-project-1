from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, List
from decimal import Decimal, ROUND_DOWN

# NOTE: Pass in the raw JSON object returned by GET /api/v3/exchangeInfo
# from the Binance(US) Spot API (developers.binance.com). This module does not
# make network calls; it only enforces rounding and trading rules.

@dataclass
class SymbolFilters:
    price_tick: Decimal
    min_price: Optional[Decimal]
    max_price: Optional[Decimal]
    qty_step: Decimal
    min_qty: Decimal
    max_qty: Optional[Decimal]
    min_notional: Optional[Decimal]
    notional_min: Optional[Decimal]
    notional_max: Optional[Decimal]
    apply_min_to_market: bool
    bid_multiplier_up: Optional[Decimal]
    ask_multiplier_up: Optional[Decimal]
    bid_multiplier_down: Optional[Decimal]
    ask_multiplier_down: Optional[Decimal]

class ExchangeFilters:
    def __init__(self, exchange_info: Dict[str, Any]):
        self.symbols: Dict[str, SymbolFilters] = {}
        for s in exchange_info.get("symbols", []):
            sym = s["symbol"]
            f = {f["filterType"]: f for f in s.get("filters", [])}
            
            price = f.get("PRICE_FILTER", {})
            lot = f.get("LOT_SIZE", {})
            min_notional = f.get("MIN_NOTIONAL", {})
            notional = f.get("NOTIONAL", {})
            pct_by_side = f.get("PERCENT_PRICE_BY_SIDE", {})  # may not exist
            
            self.symbols[sym] = SymbolFilters(
                price_tick=Decimal(price.get("tickSize", "0.00000001")),
                min_price=Decimal(price["minPrice"]) if price.get("minPrice") not in (None, "0") else None,
                max_price=Decimal(price["maxPrice"]) if price.get("maxPrice") not in (None, "0") else None,
                qty_step=Decimal(lot.get("stepSize", "0.00000001")),
                min_qty=Decimal(lot.get("minQty", "0")),
                max_qty=Decimal(lot["maxQty"]) if lot.get("maxQty") not in (None, "0") else None,
                min_notional=Decimal(min_notional["minNotional"]) if min_notional.get("minNotional") else None,
                notional_min=Decimal(notional["minNotional"]) if notional.get("minNotional") else None,
                notional_max=Decimal(notional["maxNotional"]) if notional.get("maxNotional") else None,
                apply_min_to_market=bool(min_notional.get("applyToMarket", True)) or bool(notional.get("applyMinToMarket", True)),
                bid_multiplier_up=Decimal(pct_by_side["bidMultiplierUp"]) if pct_by_side.get("bidMultiplierUp") else None,
                ask_multiplier_up=Decimal(pct_by_side["askMultiplierUp"]) if pct_by_side.get("askMultiplierUp") else None,
                bid_multiplier_down=Decimal(pct_by_side["bidMultiplierDown"]) if pct_by_side.get("bidMultiplierDown") else None,
                ask_multiplier_down=Decimal(pct_by_side["askMultiplierDown"]) if pct_by_side.get("askMultiplierDown") else None,
            )

    @staticmethod
    def _round_down(x: Decimal, step: Decimal) -> Decimal:
        """Round x down to a multiple of step"""
        q = (x / step).to_integral_value(rounding=ROUND_DOWN)
        return (q * step).quantize(step)

    def _clamp_price(self, price: Decimal, sf: SymbolFilters) -> Decimal:
        """Clamp to permissible range and tick"""
        price = self._round_down(price, sf.price_tick)
        if sf.min_price is not None and price < sf.min_price:
            price = sf.min_price
        if sf.max_price is not None and sf.max_price != 0 and price > sf.max_price:
            price = sf.max_price
        return price

    def _round_qty(self, qty: Decimal, sf: SymbolFilters) -> Decimal:
        if qty < sf.min_qty:
            qty = sf.min_qty
        qty = self._round_down(qty, sf.qty_step)
        if sf.max_qty and qty > sf.max_qty:
            qty = sf.max_qty
        return qty

    def preflight_order(
        self,
        symbol: str,
        side: str,
        price: Optional[float],
        qty: float,
        is_market: bool = True,
        ref_price: Optional[float] = None,
    ) -> Tuple[Decimal, Optional[Decimal]]:
        """
        Validate and adjust an order before sending it.
        Returns (qty_dec, price_dec or None). Raises ValueError on violation.
        
        - If is_market is True, price can be None; ref_price is used for minNotional checks.
        - Enforces MIN_NOTIONAL/NOTIONAL and LOT_SIZE.
        - Applies PRICE_FILTER tick rounding.
        - PERCENT_PRICE_BY_SIDE (if present) should be enforced by caller with best bid/ask.
        """
        sym = symbol.replace('/', '').upper()
        if sym not in self.symbols:
            raise ValueError(f"Unknown symbol {sym} in exchange info")
        
        sf = self.symbols[sym]
        qty_dec = Decimal(str(qty))
        price_dec = None
        
        if not is_market:
            if price is None:
                raise ValueError("Limit order requires price")
            price_dec = self._clamp_price(Decimal(str(price)), sf)
        
        # Round quantity
        qty_dec = self._round_qty(qty_dec, sf)
        
        # Min notional checks
        # Use ref_price for market orders. If not given, caller should pass last or mid price.
        eff_price = price_dec if price_dec is not None else Decimal(str(ref_price or 0))
        
        if (sf.min_notional or sf.notional_min) and eff_price:
            minimum = sf.min_notional or sf.notional_min
            notional = eff_price * qty_dec
            if notional < minimum:
                # Raise instead of silently bumping size to avoid accidental oversizing
                raise ValueError(f"Order notional {notional} below minimum {minimum} for {sym}")
        
        # (optional) enforce NOTIONAL max
        if sf.notional_max and eff_price:
            if eff_price * qty_dec > sf.notional_max:
                raise ValueError(f"Order notional exceeds NOTIONAL.max for {sym}")
        
        return qty_dec, price_dec