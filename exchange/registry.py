from typing import Optional
from .binanceus_client import BinanceUSClient
try:
    from .coinbase_client import CoinbaseClient
except Exception:
    CoinbaseClient = None  # optional

class ExchangeRegistry:
    def __init__(self, default: str = "binanceus"):
        self.default = default
        self._clients = {}

    def get(self, name: Optional[str] = None):
        name = (name or self.default).lower()
        if name not in self._clients:
            if name == "binanceus":
                self._clients[name] = BinanceUSClient()
            elif name == "coinbase":
                if CoinbaseClient is None:
                    raise RuntimeError("Coinbase client not available")
                self._clients[name] = CoinbaseClient()
            else:
                raise ValueError(f"Unsupported exchange: {name}")
        return self._clients[name]
