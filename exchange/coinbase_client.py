import os
from typing import Optional, Dict, Any
import ccxt
import pandas as pd

class CoinbaseClient:
    """
    Minimal Coinbase Spot client via CCXT
    - Designed to be drop-in similar to existing BinanceUSClient methods where possible
    - Keys optional; read-only if missing
    """
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, passphrase: Optional[str] = None, sandbox: bool = False):
        api_key = api_key or os.getenv("COINBASE_API_KEY")
        api_secret = api_secret or os.getenv("COINBASE_API_SECRET")
        passphrase = passphrase or os.getenv("COINBASE_API_PASSPHRASE")
        sandbox = sandbox or (os.getenv("COINBASE_USE_SANDBOX", "false").lower() == "true")

        opts = {
            'enableRateLimit': True,
        }
        if api_key and api_secret and passphrase:
            opts.update({'apiKey': api_key, 'secret': api_secret, 'password': passphrase})

        # coinbase or coinbasepro depending on ccxt version; coinbasepro is deprecated; use coinbase
        self.exchange = ccxt.coinbase(opts)
        if sandbox:
            # CCXT coinbase sandbox may require different host; if unsupported, we keep live endpoints but read-only
            self.exchange.set_sandbox_mode(True)
        self.exchange.load_markets()

    def fetch_ohlcv_15m(self, symbol: str, limit: int = 300) -> pd.DataFrame:
        o = self.exchange.fetch_ohlcv(symbol, timeframe="15m", limit=limit)
        df = pd.DataFrame(o, columns=["timestamp","open","high","low","close","volume"]).astype({"open":"float","high":"float","low":"float","close":"float","volume":"float"})
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        return df.set_index("timestamp")

    def fetch_ticker_price(self, symbol: str) -> float:
        return float(self.exchange.fetch_ticker(symbol)["last"])

    def fetch_orderbook_top(self, symbol: str):
        ob = self.exchange.fetch_order_book(symbol, limit=5)
        bid = float(ob["bids"][0][0]) if ob["bids"] else None
        ask = float(ob["asks"][0][0]) if ob["asks"] else None
        return bid, ask

    def get_equity(self, quote_symbol: str = "USD") -> float:
        try:
            bal = self.exchange.fetch_balance()
            return float(bal.get(quote_symbol, {}).get("total", 0.0) or 0.0)
        except Exception:
            return 0.0

    def get_market_lot_step(self, symbol: str) -> float:
        m = self.exchange.market(symbol); step = 1e-6
        if "precision" in m and "amount" in m["precision"]:
            step = 10 ** (-m["precision"]["amount"])
        return float(step)

    def get_price_step(self, symbol: str) -> float:
        m = self.exchange.market(symbol); step = 1e-8
        if "precision" in m and "price" in m["precision"]:
            step = 10 ** (-m["precision"]["price"])
        return float(step)

    # Market orders
    def place_market_buy(self, symbol: str, amount: float) -> Dict[str, Any]:
        return self.exchange.create_order(symbol, type="market", side="buy", amount=amount)

    def place_market_sell(self, symbol: str, amount: float) -> Dict[str, Any]:
        return self.exchange.create_order(symbol, type="market", side="sell", amount=amount)
