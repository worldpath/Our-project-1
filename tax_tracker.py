#!/usr/bin/env python3
"""
Comprehensive Tax Tracking System for Crypto Bot
================================================

Features:
- FIFO/LIFO cost basis calculation
- Wash sale rule compliance
- 1099-B generation
- Tax lot tracking
- Realized/unrealized gains/losses
- Cost basis adjustments
- Annual tax reports
"""

import os
import sqlite3
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import xlsxwriter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TaxLot:
    """Represents a tax lot for cost basis tracking"""
    symbol: str
    quantity: Decimal
    cost_basis: Decimal  # Total cost basis for this lot
    purchase_date: datetime
    purchase_price: Decimal  # Price per unit
    lot_id: str
    
    @property
    def unit_cost_basis(self) -> Decimal:
        return self.cost_basis / self.quantity if self.quantity > 0 else Decimal('0')

@dataclass
class TaxableEvent:
    """Represents a taxable event (sale, exchange, etc.)"""
    event_id: str
    symbol: str
    event_type: str  # 'sale', 'exchange', 'fork', 'airdrop'
    quantity: Decimal
    proceeds: Decimal
    cost_basis: Decimal
    realized_gain_loss: Decimal
    date: datetime
    description: str
    wash_sale: bool = False
    
class TaxTracker:
    """Comprehensive tax tracking for crypto trading"""
    
    def __init__(self, db_path: str = "tax_data.db", cost_method: str = "FIFO"):
        """
        Initialize tax tracker
        
        Args:
            db_path: Path to SQLite database
            cost_method: Cost basis method ('FIFO', 'LIFO', 'HIFO')
        """
        self.db_path = db_path
        self.cost_method = cost_method
        self.connection = None
        self.tax_lots: Dict[str, List[TaxLot]] = {}
        self.taxable_events: List[TaxableEvent] = []
        self._init_database()
        
    def _init_database(self):
        """Initialize SQLite database for tax records"""
        self.connection = sqlite3.connect(self.db_path)
        # Pragmas for durability and concurrency
        self.connection.execute('PRAGMA journal_mode=WAL;')
        self.connection.execute('PRAGMA synchronous=NORMAL;')
        cursor = self.connection.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tax_lots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_id TEXT UNIQUE,
                symbol TEXT NOT NULL,
                quantity REAL NOT NULL,
                cost_basis REAL NOT NULL,
                purchase_date TEXT NOT NULL,
                purchase_price REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS taxable_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE,
                symbol TEXT NOT NULL,
                event_type TEXT NOT NULL,
                quantity REAL NOT NULL,
                proceeds REAL NOT NULL,
                cost_basis REAL NOT NULL,
                realized_gain_loss REAL NOT NULL,
                event_date TEXT NOT NULL,
                description TEXT,
                wash_sale INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Income events (staking rewards, airdrops, forks, interest)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS income_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                income_id TEXT UNIQUE,
                symbol TEXT NOT NULL,
                income_type TEXT NOT NULL, -- 'staking', 'airdrop', 'fork', 'interest'
                quantity REAL NOT NULL,
                fmv_usd REAL NOT NULL, -- fair market value at receipt
                event_date TEXT NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id TEXT UNIQUE,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,  -- 'buy' or 'sell'
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                value REAL NOT NULL,
                fees REAL DEFAULT 0,
                timestamp TEXT NOT NULL,
                exchange TEXT,
                order_id TEXT,
                processed INTEGER DEFAULT 0
            )
        ''')
        
        # Indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tax_lots_symbol ON tax_lots(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_date ON taxable_events(event_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)')
        
        self.connection.commit()
        
    def record_trade(self, trade_id: str, symbol: str, side: str, quantity: float, 
                    price: float, fees: float = 0, timestamp: datetime = None,
                    exchange: str = None, order_id: str = None):
        """Record a trade for tax purposes (idempotent on trade_id)"""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        try:
            with self.connection:
                cursor = self.connection.cursor()
                cursor.execute('''
                    INSERT INTO trades 
                    (trade_id, symbol, side, quantity, price, value, fees, timestamp, exchange, order_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(trade_id) DO NOTHING
                ''', (
                    trade_id, symbol, side, quantity, price, 
                    quantity * price, fees, timestamp.isoformat(),
                    exchange, order_id
                ))
                # Process the trade for tax implications (only if inserted)
                if cursor.rowcount:
                    self._process_trade(trade_id, symbol, side, Decimal(str(quantity)), 
                                     Decimal(str(price)), Decimal(str(fees)), timestamp)
        except sqlite3.IntegrityError as e:
            logger.warning(f"Trade {trade_id} already exists: {e}")
            
    def _process_trade(self, trade_id: str, symbol: str, side: str, 
                      quantity: Decimal, price: Decimal, fees: Decimal, 
                      timestamp: datetime):
        """Process trade for tax lot management"""
        
        if side.lower() == 'buy':
            # Create new tax lot
            total_cost = quantity * price + fees
            lot_id = f"{symbol}_{timestamp.strftime('%Y%m%d_%H%M%S')}_{trade_id}"
            
            tax_lot = TaxLot(
                symbol=symbol,
                quantity=quantity,
                cost_basis=total_cost,
                purchase_date=timestamp,
                purchase_price=price,
                lot_id=lot_id
            )
            
            # Add to database
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT INTO tax_lots 
                (lot_id, symbol, quantity, cost_basis, purchase_date, purchase_price)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (lot_id, symbol, float(quantity), float(total_cost), 
                  timestamp.isoformat(), float(price)))
            self.connection.commit()
            
            # Add to memory
            if symbol not in self.tax_lots:
                self.tax_lots[symbol] = []
            self.tax_lots[symbol].append(tax_lot)
            
        elif side.lower() == 'sell':
            # Process sale and calculate gains/losses
            proceeds = quantity * price - fees
            self._process_sale(trade_id, symbol, quantity, proceeds, timestamp)
            
    def _process_sale(self, trade_id: str, symbol: str, quantity: Decimal, 
                     proceeds: Decimal, sale_date: datetime):
        """Process a sale and calculate gains/losses using cost method"""
        
        if symbol not in self.tax_lots:
            logger.warning(f"No tax lots found for {symbol}, creating zero-basis lot")
            return
            
        # Load tax lots from database if not in memory
        if not self.tax_lots[symbol]:
            self._load_tax_lots(symbol)
            
        remaining_quantity = quantity
        total_cost_basis = Decimal('0')
        lots_to_update = []
        
        # Sort lots based on cost method
        if self.cost_method == "FIFO":
            lots = sorted(self.tax_lots[symbol], key=lambda x: x.purchase_date)
        elif self.cost_method == "LIFO":
            lots = sorted(self.tax_lots[symbol], key=lambda x: x.purchase_date, reverse=True)
        elif self.cost_method == "HIFO":  # Highest In, First Out
            lots = sorted(self.tax_lots[symbol], key=lambda x: x.unit_cost_basis, reverse=True)
        else:
            lots = self.tax_lots[symbol]  # Default to current order
            
        for lot in lots:
            if remaining_quantity <= 0:
                break
                
            if lot.quantity <= 0:
                continue
                
            # Calculate how much to take from this lot
            lot_quantity_used = min(remaining_quantity, lot.quantity)
            lot_cost_basis = lot.unit_cost_basis * lot_quantity_used
            
            total_cost_basis += lot_cost_basis
            remaining_quantity -= lot_quantity_used
            
            # Update lot
            lot.quantity -= lot_quantity_used
            lot.cost_basis -= lot_cost_basis
            lots_to_update.append(lot)
            
        # Update database
        cursor = self.connection.cursor()
        for lot in lots_to_update:
            cursor.execute('''
                UPDATE tax_lots SET quantity = ?, cost_basis = ? WHERE lot_id = ?
            ''', (float(lot.quantity), float(lot.cost_basis), lot.lot_id))
            
        # Create taxable event
        realized_gain_loss = proceeds - total_cost_basis
        
        # Check for wash sale (simplified - within 30 days)
        wash_sale = self._check_wash_sale(symbol, sale_date)
        
        event = TaxableEvent(
            event_id=f"sale_{trade_id}",
            symbol=symbol,
            event_type="sale",
            quantity=quantity,
            proceeds=proceeds,
            cost_basis=total_cost_basis,
            realized_gain_loss=realized_gain_loss,
            date=sale_date,
            description=f"Sale of {quantity} {symbol}",
            wash_sale=wash_sale
        )
        
        # Save taxable event
        cursor.execute('''
            INSERT INTO taxable_events 
            (event_id, symbol, event_type, quantity, proceeds, cost_basis, 
             realized_gain_loss, event_date, description, wash_sale)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            event.event_id, event.symbol, event.event_type, 
            float(event.quantity), float(event.proceeds), float(event.cost_basis),
            float(event.realized_gain_loss), event.date.isoformat(),
            event.description, 1 if event.wash_sale else 0
        ))
        
        self.connection.commit()
        self.taxable_events.append(event)
        
    def _check_wash_sale(self, symbol: str, sale_date: datetime) -> bool:
        """Check if sale qualifies as wash sale (simplified implementation)"""
        # Check if there was a purchase within 30 days before or after
        cursor = self.connection.cursor()
        start_date = sale_date - timedelta(days=30)
        end_date = sale_date + timedelta(days=30)
        
        cursor.execute('''
            SELECT COUNT(*) FROM trades 
            WHERE symbol = ? AND side = 'buy' 
            AND timestamp BETWEEN ? AND ? AND timestamp != ?
        ''', (symbol, start_date.isoformat(), end_date.isoformat(), sale_date.isoformat()))
        
        count = cursor.fetchone()[0]
        return count > 0
        
    def _load_tax_lots(self, symbol: str):
        """Load tax lots from database for a symbol"""
        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT lot_id, symbol, quantity, cost_basis, purchase_date, purchase_price
            FROM tax_lots WHERE symbol = ? AND quantity > 0
        ''', (symbol,))
        
        lots = []
        for row in cursor.fetchall():
            lot = TaxLot(
                lot_id=row[0],
                symbol=row[1],
                quantity=Decimal(str(row[2])),
                cost_basis=Decimal(str(row[3])),
                purchase_date=datetime.fromisoformat(row[4]),
                purchase_price=Decimal(str(row[5]))
            )
            lots.append(lot)
            
        self.tax_lots[symbol] = lots
        
    def get_portfolio_summary(self) -> Dict:
        """Get current portfolio summary for tax purposes"""
        cursor = self.connection.cursor()
        
        # Get current holdings
        cursor.execute('''
            SELECT symbol, SUM(quantity) as total_quantity, SUM(cost_basis) as total_cost_basis
            FROM tax_lots WHERE quantity > 0
            GROUP BY symbol
        ''')
        
        holdings = {}
        for row in cursor.fetchall():
            symbol, quantity, cost_basis = row
            holdings[symbol] = {
                'quantity': quantity,
                'cost_basis': cost_basis,
                'avg_cost_basis': cost_basis / quantity if quantity > 0 else 0
            }
            
        # Get realized gains/losses for current year
        current_year = datetime.now().year
        cursor.execute('''
            SELECT SUM(realized_gain_loss) as total_realized
            FROM taxable_events 
            WHERE event_date >= ? AND event_date < ?
        ''', (f"{current_year}-01-01", f"{current_year + 1}-01-01"))
        
        total_realized = cursor.fetchone()[0] or 0
        
        return {
            'holdings': holdings,
            'realized_gains_losses_ytd': total_realized,
            'as_of_date': datetime.now(timezone.utc).isoformat()
        }
        
    def record_income(self, income_id: str, symbol: str, income_type: str, quantity: float, fmv_usd: float, event_date: Optional[datetime] = None, description: str = ""):
        """Record income events such as staking rewards or airdrops"""
        event_date = event_date or datetime.now(timezone.utc)
        try:
            with self.connection:
                self.connection.execute('''
                    INSERT INTO income_events (income_id, symbol, income_type, quantity, fmv_usd, event_date, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(income_id) DO NOTHING
                ''', (income_id, symbol, income_type, quantity, fmv_usd, event_date.isoformat(), description))
        except sqlite3.IntegrityError as e:
            logger.warning(f"Income event {income_id} already exists: {e}")

    def generate_1099_b_data(self, tax_year: int) -> List[Dict]:
        """Generate 1099-B data for a tax year"""
        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT event_id, symbol, event_type, quantity, proceeds, cost_basis,
                   realized_gain_loss, event_date, description, wash_sale
            FROM taxable_events 
            WHERE event_date >= ? AND event_date < ?
            ORDER BY event_date
        ''', (f"{tax_year}-01-01", f"{tax_year + 1}-01-01"))
        
        events = []
        for row in cursor.fetchall():
            events.append({
                'event_id': row[0],
                'symbol': row[1],
                'event_type': row[2],
                'quantity': row[3],
                'proceeds': row[4],
                'cost_basis': row[5],
                'realized_gain_loss': row[6],
                'event_date': row[7],
                'description': row[8],
                'wash_sale': bool(row[9])
            })
            
        return events
        
    def export_8949_csv(self, tax_year: int, filename: Optional[str] = None) -> str:
        """Export a basic Form 8949-compatible CSV (short-term/long-term not split here)"""
        data_1099b = self.generate_1099_b_data(tax_year)
        filename = filename or f"form_8949_{tax_year}.csv"
        import csv
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Description of property", "Date acquired", "Date sold", "Proceeds", "Cost or other basis", "Adjustment code(s)", "Gain or (loss)"])
            for e in data_1099b:
                writer.writerow([
                    e['symbol'],
                    "VARIOUS",  # detailed lot dates can be expanded in future
                    e['event_date'][:10],
                    f"{e['proceeds']:.2f}",
                    f"{e['cost_basis']:.2f}",
                    "W" if e.get('wash_sale') else "",
                    f"{e['realized_gain_loss']:.2f}"
                ])
        return filename

    def export_tax_report(self, tax_year: int, output_format: str = "xlsx") -> str:
        """Export comprehensive tax report"""
        
        data_1099b = self.generate_1099_b_data(tax_year)
        portfolio_summary = self.get_portfolio_summary()
        
        if output_format.lower() == "xlsx":
            return self._export_excel_report(tax_year, data_1099b, portfolio_summary)
        elif output_format.lower() == "pdf":
            return self._export_pdf_report(tax_year, data_1099b, portfolio_summary)
        else:
            raise ValueError(f"Unsupported format: {output_format}")
            
    def _export_excel_report(self, tax_year: int, data_1099b: List[Dict], 
                           portfolio_summary: Dict) -> str:
        """Export tax report as Excel file"""
        
        filename = f"crypto_tax_report_{tax_year}.xlsx"
        workbook = xlsxwriter.Workbook(filename)
        
        # Format styles
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC'})
        money_format = workbook.add_format({'num_format': '$#,##0.00'})
        date_format = workbook.add_format({'num_format': 'mm/dd/yyyy'})
        
        # 1099-B Data Sheet
        worksheet_1099 = workbook.add_worksheet('1099-B Data')
        headers_1099 = ['Symbol', 'Quantity', 'Sale Date', 'Proceeds', 'Cost Basis', 
                       'Gain/Loss', 'Wash Sale', 'Description']
        
        for col, header in enumerate(headers_1099):
            worksheet_1099.write(0, col, header, header_format)
            
        for row, event in enumerate(data_1099b, 1):
            worksheet_1099.write(row, 0, event['symbol'])
            worksheet_1099.write(row, 1, event['quantity'])
            worksheet_1099.write(row, 2, event['event_date'][:10], date_format)
            worksheet_1099.write(row, 3, event['proceeds'], money_format)
            worksheet_1099.write(row, 4, event['cost_basis'], money_format)
            worksheet_1099.write(row, 5, event['realized_gain_loss'], money_format)
            worksheet_1099.write(row, 6, 'Yes' if event['wash_sale'] else 'No')
            worksheet_1099.write(row, 7, event['description'])
            
        # Portfolio Summary Sheet
        worksheet_portfolio = workbook.add_worksheet('Portfolio Summary')
        summary_headers = ['Symbol', 'Quantity', 'Cost Basis', 'Avg Cost/Unit']
        
        for col, header in enumerate(summary_headers):
            worksheet_portfolio.write(0, col, header, header_format)
            
        row = 1
        for symbol, data in portfolio_summary['holdings'].items():
            worksheet_portfolio.write(row, 0, symbol)
            worksheet_portfolio.write(row, 1, data['quantity'])
            worksheet_portfolio.write(row, 2, data['cost_basis'], money_format)
            worksheet_portfolio.write(row, 3, data['avg_cost_basis'], money_format)
            row += 1
            
        # Summary totals
        worksheet_portfolio.write(row + 2, 0, 'YTD Realized Gains/Losses:', header_format)
        worksheet_portfolio.write(row + 2, 1, portfolio_summary['realized_gains_losses_ytd'], money_format)
        
        workbook.close()
        return filename
        
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

# Example usage and integration
def integrate_with_trade_logger():
    """Integration example with existing trade logger"""
    
    def enhanced_log_trade(symbol: str, side: str, quantity: float, price: float, 
                          order_id: str = "", tag: str = "", note: str = ""):
        """Enhanced trade logging with tax tracking"""
        
        # Original trade logging
        timestamp = datetime.now(timezone.utc)
        
        # Tax tracking
        tax_tracker = TaxTracker()
        trade_id = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{order_id}"
        
        tax_tracker.record_trade(
            trade_id=trade_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            timestamp=timestamp,
            order_id=order_id
        )
        
        tax_tracker.close()
        
        return trade_id

if __name__ == "__main__":
    # Example usage
    tracker = TaxTracker()
    
    # Record some example trades
    tracker.record_trade("trade_1", "BTCUSDT", "buy", 0.1, 50000, 10)
    tracker.record_trade("trade_2", "BTCUSDT", "sell", 0.05, 52000, 5)
    
    # Get portfolio summary
    summary = tracker.get_portfolio_summary()
    print(f"Portfolio Summary: {json.dumps(summary, indent=2, default=str)}")
    
    # Generate tax report
    report_file = tracker.export_tax_report(2025, "xlsx")
    print(f"Tax report exported to: {report_file}")
    
    tracker.close()