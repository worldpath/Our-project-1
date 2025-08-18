
import os, ccxt, pandas as pd
from typing import Optional, Dict, Any
from datetime import datetime, timezone

class BinanceUSClient:
    def __init__(self, api_key: Optional[str]=None, api_secret: Optional[str]=None):
        api_key = api_key or os.getenv("BINANCEUS_API_KEY")
        api_secret = api_secret or os.getenv("BINANCEUS_API_SECRET")
        self.exchange = ccxt.binanceus({
            "apiKey": api_key, "secret": api_secret,
            "enableRateLimit": True, "options": {"adjustForTimeDifference": True}
        })
        self.exchange.load_markets()

    def fetch_ohlcv_15m(self, symbol: str, limit: int=500) -> pd.DataFrame:
        o = self.exchange.fetch_ohlcv(symbol, timeframe="15m", limit=limit)
        df = pd.DataFrame(o, columns=["timestamp","open","high","low","close","volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        return df.set_index("timestamp")

    def get_equity(self, quote_symbol: str="USDT") -> float:
        bal = self.exchange.fetch_balance()
        tot = bal.get(quote_symbol,{}).get("total",0.0) or 0.0
        return float(tot)

    def get_market_lot_step(self, symbol: str) -> float:
        m = self.exchange.market(symbol); step = 1e-6
        if "precision" in m and "amount" in m["precision"]:
            step = 10**(-m["precision"]["amount"])
        return float(step)

    def get_price_step(self, symbol: str) -> float:
        m = self.exchange.market(symbol); step = 1e-8
        if "precision" in m and "price" in m["precision"]:
            step = 10**(-m["precision"]["price"])
        return float(step)

    def fetch_orderbook_top(self, symbol: str):
        ob = self.exchange.fetch_order_book(symbol, limit=5)
        bid = float(ob["bids"][0][0]) if ob["bids"] else None
        ask = float(ob["asks"][0][0]) if ob["asks"] else None
        return bid, ask

    def fetch_ticker_price(self, symbol: str) -> float:
        return float(self.exchange.fetch_ticker(symbol)["last"])

    def place_market_buy(self, symbol: str, amount: float) -> Dict[str,Any]:
        return self.exchange.create_order(symbol, type="market", side="buy", amount=amount)

    def place_market_sell(self, symbol: str, amount: float) -> Dict[str,Any]:
        return self.exchange.create_order(symbol, type="market", side="sell", amount=amount)

    def place_limit_maker_buy(self, symbol: str, amount: float, price: float):
        return self.exchange.create_order(symbol, type="limit_maker", side="buy", amount=amount, price=price)

    def place_limit_maker_sell(self, symbol: str, amount: float, price: float):
        return self.exchange.create_order(symbol, type="limit_maker", side="sell", amount=amount, price=price)

    def place_limit_sell(self, symbol: str, amount: float, price: float):
        return self.exchange.create_order(symbol, type="limit", side="sell", amount=amount, price=price)

    def place_stop_limit_sell(self, symbol: str, amount: float, stop_price: float, limit_price: float):
        params = {"stopPrice": self.exchange.price_to_precision(symbol, stop_price), "timeInForce": "GTC"}
        return self.exchange.create_order(symbol, type="limit", side="sell", amount=amount, price=limit_price, params=params)

    def place_oco_sell(self, symbol: str, amount: float, tp_price: float, stop_price: float, stop_limit_price: float):
        # ccxt raw endpoint
        return self.exchange.private_post_order_oco({
            "symbol": self.exchange.market_id(symbol),
            "side": "SELL",
            "quantity": self.exchange.amount_to_precision(symbol, amount),
            "price": self.exchange.price_to_precision(symbol, tp_price),
            "stopPrice": self.exchange.price_to_precision(symbol, stop_price),
            "stopLimitPrice": self.exchange.price_to_precision(symbol, stop_limit_price),
            "stopLimitTimeInForce": "GTC",
        })
