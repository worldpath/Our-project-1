# Enhanced trade_logger.py with tax tracking integration
import csv
from datetime import datetime, timezone
from typing import Optional
import logging

# Import tax tracker if available
try:
    from tax_tracker import TaxTracker
    TAX_TRACKING_AVAILABLE = True
except ImportError:
    TAX_TRACKING_AVAILABLE = False
    logging.warning("Tax tracking not available - tax_tracker.py not found")

class TradeLogger:
    """
    Enhanced CSV trade logger with tax tracking integration.
    Columns:
      timestamp_utc, symbol, side, qty, price, order_id, tag, note, pnl_quote, fees
    """
    def __init__(self, filepath: str = "trade_history.csv", enable_tax_tracking: bool = True):
        self.filepath = filepath
        self.enable_tax_tracking = enable_tax_tracking and TAX_TRACKING_AVAILABLE
        
        # Initialize tax tracker if enabled
        if self.enable_tax_tracking:
            try:
                self.tax_tracker = TaxTracker()
                logging.info("Tax tracking enabled")
            except Exception as e:
                logging.error(f"Failed to initialize tax tracker: {e}")
                self.enable_tax_tracking = False
                
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
                    "fees",
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
        fees: float = 0.0,
    ):
        ts = datetime.now(timezone.utc)
        
        # Log to CSV file
        with open(self.filepath, "a", newline="") as f:
            csv.writer(f).writerow([
                ts.isoformat(),
                symbol,
                side,
                f"{qty:.10f}",
                f"{price:.8f}",
                order_id,
                tag,
                note,
                "" if pnl_quote is None else f"{pnl_quote:.2f}",
                f"{fees:.8f}",
            ])
            
        # Log to tax tracker if enabled
        if self.enable_tax_tracking:
            try:
                trade_id = f"{ts.strftime('%Y%m%d_%H%M%S')}_{order_id}" if order_id else f"{ts.strftime('%Y%m%d_%H%M%S')}_{symbol}_{side}"
                
                self.tax_tracker.record_trade(
                    trade_id=trade_id,
                    symbol=symbol,
                    side=side,
                    quantity=qty,
                    price=price,
                    fees=fees,
                    timestamp=ts,
                    order_id=order_id
                )
                
                logging.debug(f"Tax tracking recorded for trade: {trade_id}")
                
            except Exception as e:
                logging.error(f"Failed to record trade for tax tracking: {e}")
                
        # Console logging
        logging.info(f"[TRADE] {ts.isoformat()} {symbol} {side} {qty:.8f} @ {price:.4f} fees={fees:.4f} {tag} {note}")
        
    def close(self):
        """Close resources and cleanup"""
        if hasattr(self, 'tax_tracker'):
            try:
                self.tax_tracker.close()
                logging.info("Tax tracker closed successfully")
            except Exception as e:
                logging.error(f"Error closing tax tracker: {e}")
                
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
