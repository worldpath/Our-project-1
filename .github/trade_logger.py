# trade_logger.py
import csv
from datetime import datetime, timezone
from typing import Optional

class TradeLogger:
    """
    CSV trade logger. Appends rows as trades occur.
    Columns:
      timestamp_utc, symbol, side, qty, price, order_id, tag, note, pnl_quote
    """
    def __init__(self, filepath: str = "trade_history.csv"):
        self.filepath = filepath
        try:
            # Create file with header if it doesn't exist
            with open(self.filepath, "x", newline="") as f:
                csv.writer(f).writerow([
                    "timestamp_utc",
                    "symbol",
                    "side",
                    "qty",
                    "price",
                    "order_id",
                    "tag",
                    "note",
                    "pnl_quote",
                ])
        except FileExistsError:
            pass

    def log(
        self,
        symbol: str,
        side: str,
        qty: float,
        price: float,
        order_id: str = "",
        tag: str = "",
        note: str = "",
        pnl_quote: Optional[float] = None,
    ):
        ts = datetime.now(timezone.utc).isoformat()
        with open(self.filepath, "a", newline="") as f:
            csv.writer(f).writerow([
                ts,
                symbol,
                side,
                f"{qty:.10f}",
                f"{price:.8f}",
                order_id,
                tag,
                note,
                "" if pnl_quote is None else f"{pnl_quote:.2f}",
            ])
