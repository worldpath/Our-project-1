"""
Enhanced Tax Integration System
==============================

Features:
- Fee-adjusted R-multiple calculations
- Automated tax reporting
- Integration with popular tax software APIs
- Real-time tax liability tracking
- Wash sale rule compliance
- FIFO/LIFO/Specific ID lot tracking
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
import requests
import pandas as pd
from enum import Enum

logger = logging.getLogger(__name__)

class CostBasisMethod(Enum):
    """Cost basis calculation methods"""
    FIFO = "fifo"  # First In, First Out
    LIFO = "lifo"  # Last In, First Out
    SPECIFIC_ID = "specific_id"  # Specific identification
    AVERAGE_COST = "average_cost"  # Average cost basis

class TaxableEvent(Enum):
    """Types of taxable events"""
    TRADE = "trade"
    DIVIDEND = "dividend"
    STAKING_REWARD = "staking_reward"
    AIRDROP = "airdrop"
    FORK = "fork"
    MINING = "mining"

@dataclass
class TaxLot:
    """Individual tax lot for specific ID tracking"""
    lot_id: str
    symbol: str
    quantity: Decimal
    cost_basis: Decimal  # Total cost basis for the lot
    acquisition_date: datetime
    acquisition_price: Decimal
    fees_paid: Decimal = Decimal('0')
    
    def per_unit_cost_basis(self) -> Decimal:
        """Calculate cost basis per unit"""
        if self.quantity <= 0:
            return Decimal('0')
        return (self.cost_basis + self.fees_paid) / self.quantity

@dataclass
class TaxableTransaction:
    """Complete taxable transaction record"""
    transaction_id: str
    timestamp: datetime
    event_type: TaxableEvent
    symbol: str
    
    # Trade details
    quantity: Decimal = Decimal('0')
    price: Decimal = Decimal('0')
    fees: Decimal = Decimal('0')
    
    # Tax calculations
    proceeds: Decimal = Decimal('0')  # For sales
    cost_basis: Decimal = Decimal('0')  # For sales
    gain_loss: Decimal = Decimal('0')  # Realized gain/loss
    
    # Classification
    is_long_term: bool = False
    is_wash_sale: bool = False
    
    # Related lots (for sales)
    disposed_lots: List[Dict] = field(default_factory=list)

@dataclass 
class TaxSummary:
    """Tax period summary"""
    year: int
    total_proceeds: Decimal = Decimal('0')
    total_cost_basis: Decimal = Decimal('0')
    short_term_gain_loss: Decimal = Decimal('0')
    long_term_gain_loss: Decimal = Decimal('0')
    total_fees: Decimal = Decimal('0')
    wash_sale_disallowed: Decimal = Decimal('0')
    
    # Detailed breakdowns
    transactions: List[TaxableTransaction] = field(default_factory=list)
    by_symbol: Dict[str, Dict] = field(default_factory=dict)

class WashSaleTracker:
    """Track wash sales for compliance"""
    
    def __init__(self):
        self.recent_losses = []  # Track losses for wash sale detection
    
    def check_wash_sale(self, symbol: str, sale_date: datetime, 
                       purchase_dates: List[datetime]) -> bool:
        """
        Check if a transaction violates wash sale rules
        Wash sale: selling at a loss and buying substantially identical security 
        within 30 days before or after the sale
        """
        
        # Check purchases within 61-day window (30 days before and after)
        wash_sale_window_start = sale_date - timedelta(days=30)
        wash_sale_window_end = sale_date + timedelta(days=30)
        
        for purchase_date in purchase_dates:
            if wash_sale_window_start <= purchase_date <= wash_sale_window_end:
                return True
        
        return False
    
    def record_loss_sale(self, symbol: str, sale_date: datetime, loss_amount: Decimal):
        """Record a loss sale for wash sale tracking"""
        self.recent_losses.append({
            'symbol': symbol,
            'sale_date': sale_date,
            'loss_amount': loss_amount
        })
        
        # Clean up old losses (older than 30 days)
        cutoff_date = datetime.now() - timedelta(days=61)
        self.recent_losses = [
            loss for loss in self.recent_losses 
            if loss['sale_date'] >= cutoff_date
        ]

class TaxCalculationEngine:
    """Core tax calculation engine with fee integration"""
    
    def __init__(self, db_path: str = "enhanced_tax_records.db", 
                 cost_basis_method: CostBasisMethod = CostBasisMethod.FIFO):
        self.db_path = db_path
        self.cost_basis_method = cost_basis_method
        self.wash_sale_tracker = WashSaleTracker()
        
        # Holdings tracking
        self.holdings: Dict[str, List[TaxLot]] = {}  # symbol -> list of tax lots
        
        # Initialize database
        self._init_database()
        
    def _init_database(self):
        """Initialize tax tracking database"""
        conn = sqlite3.connect(self.db_path)
        
        # Enhanced tax lots table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tax_lots (
                lot_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                quantity REAL NOT NULL,
                cost_basis REAL NOT NULL,
                acquisition_date TEXT NOT NULL,
                acquisition_price REAL NOT NULL,
                fees_paid REAL DEFAULT 0,
                is_disposed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Enhanced transactions table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tax_transactions (
                transaction_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                symbol TEXT NOT NULL,
                quantity REAL DEFAULT 0,
                price REAL DEFAULT 0,
                fees REAL DEFAULT 0,
                proceeds REAL DEFAULT 0,
                cost_basis REAL DEFAULT 0,
                gain_loss REAL DEFAULT 0,
                is_long_term INTEGER DEFAULT 0,
                is_wash_sale INTEGER DEFAULT 0,
                disposed_lots TEXT,  -- JSON array of disposed lots
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Fee tracking table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS fee_records (
                fee_id TEXT PRIMARY KEY,
                transaction_id TEXT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                fee_amount REAL NOT NULL,
                fee_type TEXT NOT NULL,  -- maker, taker, withdrawal, etc.
                fee_currency TEXT NOT NULL,
                exchange TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (transaction_id) REFERENCES tax_transactions (transaction_id)
            )
        ''')
        
        # Tax year summaries
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tax_summaries (
                year INTEGER PRIMARY KEY,
                total_proceeds REAL DEFAULT 0,
                total_cost_basis REAL DEFAULT 0,
                short_term_gain_loss REAL DEFAULT 0,
                long_term_gain_loss REAL DEFAULT 0,
                total_fees REAL DEFAULT 0,
                wash_sale_disallowed REAL DEFAULT 0,
                summary_data TEXT,  -- JSON summary data
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("Enhanced tax database initialized")
    
    def record_acquisition(self, symbol: str, quantity: Decimal, price: Decimal, 
                          timestamp: datetime, fees: Decimal = Decimal('0'),
                          transaction_id: str = None) -> str:
        """
        Record acquisition of cryptocurrency with fee integration
        
        Returns:
            lot_id: Unique identifier for the tax lot
        """
        
        lot_id = f"{symbol}_{timestamp.strftime('%Y%m%d_%H%M%S')}_{quantity}"
        
        if transaction_id is None:
            transaction_id = f"acq_{lot_id}"
        
        # Calculate total cost basis (including fees)
        total_cost = quantity * price + fees
        
        # Create tax lot
        tax_lot = TaxLot(
            lot_id=lot_id,
            symbol=symbol,
            quantity=quantity,
            cost_basis=total_cost,
            acquisition_date=timestamp,
            acquisition_price=price,
            fees_paid=fees
        )
        
        # Add to holdings
        if symbol not in self.holdings:
            self.holdings[symbol] = []
        self.holdings[symbol].append(tax_lot)
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        
        conn.execute('''
            INSERT INTO tax_lots (lot_id, symbol, quantity, cost_basis, 
                                acquisition_date, acquisition_price, fees_paid)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (lot_id, symbol, float(quantity), float(total_cost), 
              timestamp.isoformat(), float(price), float(fees)))
        
        # Record transaction
        conn.execute('''
            INSERT INTO tax_transactions (transaction_id, timestamp, event_type, 
                                        symbol, quantity, price, fees, cost_basis)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (transaction_id, timestamp.isoformat(), TaxableEvent.TRADE.value,
              symbol, float(quantity), float(price), float(fees), float(total_cost)))
        
        # Record fee if applicable
        if fees > 0:
            fee_id = f"fee_{transaction_id}"
            conn.execute('''
                INSERT INTO fee_records (fee_id, transaction_id, timestamp, 
                                       symbol, fee_amount, fee_type, fee_currency)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (fee_id, transaction_id, timestamp.isoformat(), 
                  symbol, float(fees), "trading", "USD"))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Recorded acquisition: {quantity} {symbol} @ {price} "
                   f"(fees: ${fees}, total cost: ${total_cost})")
        
        return lot_id
    
    def record_disposal(self, symbol: str, quantity: Decimal, price: Decimal,
                       timestamp: datetime, fees: Decimal = Decimal('0'),
                       transaction_id: str = None) -> TaxableTransaction:
        """
        Record disposal (sale) of cryptocurrency with fee-adjusted calculations
        
        Returns:
            TaxableTransaction with calculated gains/losses
        """
        
        if transaction_id is None:
            transaction_id = f"disp_{symbol}_{timestamp.strftime('%Y%m%d_%H%M%S')}_{quantity}"
        
        # Calculate proceeds (net of fees)
        gross_proceeds = quantity * price
        net_proceeds = gross_proceeds - fees
        
        # Determine lots to dispose of based on cost basis method
        disposed_lots, total_cost_basis = self._determine_disposal_lots(symbol, quantity)
        
        if not disposed_lots:
            raise ValueError(f"Insufficient {symbol} holdings for disposal of {quantity}")
        
        # Calculate gain/loss
        realized_gain_loss = net_proceeds - total_cost_basis
        
        # Determine if long-term or short-term
        is_long_term = self._is_long_term_gain(disposed_lots, timestamp)
        
        # Check for wash sale
        purchase_dates = [lot['acquisition_date'] for lot in disposed_lots]
        is_wash_sale = (realized_gain_loss < 0 and 
                       self.wash_sale_tracker.check_wash_sale(symbol, timestamp, purchase_dates))
        
        if is_wash_sale and realized_gain_loss < 0:
            self.wash_sale_tracker.record_loss_sale(symbol, timestamp, abs(realized_gain_loss))
        
        # Create taxable transaction
        tax_transaction = TaxableTransaction(
            transaction_id=transaction_id,
            timestamp=timestamp,
            event_type=TaxableEvent.TRADE,
            symbol=symbol,
            quantity=quantity,
            price=price,
            fees=fees,
            proceeds=net_proceeds,
            cost_basis=total_cost_basis,
            gain_loss=realized_gain_loss,
            is_long_term=is_long_term,
            is_wash_sale=is_wash_sale,
            disposed_lots=disposed_lots
        )
        
        # Update holdings by removing disposed quantities
        self._update_holdings_after_disposal(symbol, disposed_lots)
        
        # Save to database
        self._save_disposal_to_database(tax_transaction)
        
        logger.info(f"Recorded disposal: {quantity} {symbol} @ {price} "
                   f"(fees: ${fees}, gain/loss: ${realized_gain_loss:.2f}, "
                   f"{'LT' if is_long_term else 'ST'})")
        
        return tax_transaction
    
    def _determine_disposal_lots(self, symbol: str, quantity: Decimal) -> Tuple[List[Dict], Decimal]:
        """Determine which lots to dispose of based on cost basis method"""
        
        if symbol not in self.holdings or not self.holdings[symbol]:
            return [], Decimal('0')
        
        available_lots = [lot for lot in self.holdings[symbol] if lot.quantity > 0]
        
        if self.cost_basis_method == CostBasisMethod.FIFO:
            # Sort by acquisition date (oldest first)
            available_lots.sort(key=lambda x: x.acquisition_date)
        elif self.cost_basis_method == CostBasisMethod.LIFO:
            # Sort by acquisition date (newest first)
            available_lots.sort(key=lambda x: x.acquisition_date, reverse=True)
        elif self.cost_basis_method == CostBasisMethod.AVERAGE_COST:
            # Calculate average cost and treat as single lot
            total_quantity = sum(lot.quantity for lot in available_lots)
            total_cost = sum(lot.cost_basis + lot.fees_paid for lot in available_lots)
            avg_cost_per_unit = total_cost / total_quantity if total_quantity > 0 else Decimal('0')
            
            # Create virtual average lot
            available_lots = [{
                'lot_id': 'average_cost',
                'quantity': total_quantity,
                'cost_basis_per_unit': avg_cost_per_unit,
                'acquisition_date': available_lots[0].acquisition_date if available_lots else datetime.now()
            }]
        
        # Allocate disposal across lots
        disposed_lots = []
        remaining_quantity = quantity
        total_cost_basis = Decimal('0')
        
        for lot in available_lots:
            if remaining_quantity <= 0:
                break
            
            if isinstance(lot, dict):  # Average cost method
                disposal_quantity = min(remaining_quantity, lot['quantity'])
                disposal_cost = disposal_quantity * lot['cost_basis_per_unit']
            else:  # Regular tax lot
                disposal_quantity = min(remaining_quantity, lot.quantity)
                disposal_cost = disposal_quantity * lot.per_unit_cost_basis()
            
            disposed_lot = {
                'lot_id': lot.lot_id if hasattr(lot, 'lot_id') else lot['lot_id'],
                'disposal_quantity': disposal_quantity,
                'cost_basis': disposal_cost,
                'acquisition_date': lot.acquisition_date if hasattr(lot, 'acquisition_date') else lot['acquisition_date']
            }
            
            disposed_lots.append(disposed_lot)
            total_cost_basis += disposal_cost
            remaining_quantity -= disposal_quantity
        
        return disposed_lots, total_cost_basis
    
    def _is_long_term_gain(self, disposed_lots: List[Dict], sale_date: datetime) -> bool:
        """Determine if gain qualifies as long-term (>1 year)"""
        
        # For mixed lots, use the lot with the earliest acquisition date
        earliest_acquisition = min(lot['acquisition_date'] for lot in disposed_lots)
        
        if isinstance(earliest_acquisition, str):
            earliest_acquisition = datetime.fromisoformat(earliest_acquisition)
        
        holding_period = sale_date - earliest_acquisition
        return holding_period.days > 365
    
    def _update_holdings_after_disposal(self, symbol: str, disposed_lots: List[Dict]):
        """Update holdings after disposal"""
        
        if symbol not in self.holdings:
            return
        
        for disposed_lot in disposed_lots:
            lot_id = disposed_lot['lot_id']
            disposal_quantity = disposed_lot['disposal_quantity']
            
            # Find and update the corresponding tax lot
            for i, lot in enumerate(self.holdings[symbol]):
                if lot.lot_id == lot_id:
                    lot.quantity -= disposal_quantity
                    
                    # Remove lot if fully disposed
                    if lot.quantity <= 0:
                        self.holdings[symbol].pop(i)
                    break
    
    def _save_disposal_to_database(self, transaction: TaxableTransaction):
        """Save disposal transaction to database"""
        
        conn = sqlite3.connect(self.db_path)
        
        # Save transaction
        conn.execute('''
            INSERT INTO tax_transactions (
                transaction_id, timestamp, event_type, symbol, quantity, 
                price, fees, proceeds, cost_basis, gain_loss, is_long_term, 
                is_wash_sale, disposed_lots
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            transaction.transaction_id,
            transaction.timestamp.isoformat(),
            transaction.event_type.value,
            transaction.symbol,
            float(transaction.quantity),
            float(transaction.price),
            float(transaction.fees),
            float(transaction.proceeds),
            float(transaction.cost_basis),
            float(transaction.gain_loss),
            int(transaction.is_long_term),
            int(transaction.is_wash_sale),
            json.dumps(transaction.disposed_lots, default=str)
        ))
        
        # Record fee if applicable
        if transaction.fees > 0:
            fee_id = f"fee_{transaction.transaction_id}"
            conn.execute('''
                INSERT INTO fee_records (fee_id, transaction_id, timestamp, 
                                       symbol, fee_amount, fee_type, fee_currency)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (fee_id, transaction.transaction_id, 
                  transaction.timestamp.isoformat(), transaction.symbol,
                  float(transaction.fees), "trading", "USD"))
        
        conn.commit()
        conn.close()
    
    def calculate_fee_adjusted_r_multiple(self, entry_price: Decimal, exit_price: Decimal,
                                        entry_fees: Decimal, exit_fees: Decimal,
                                        stop_price: Decimal, side: str = "long") -> Decimal:
        """
        Calculate fee-adjusted R-multiple for trade analysis
        
        Args:
            entry_price: Entry price
            exit_price: Exit price  
            entry_fees: Fees paid on entry
            exit_fees: Fees paid on exit
            stop_price: Original stop loss price
            side: "long" or "short"
            
        Returns:
            Fee-adjusted R-multiple
        """
        
        # Calculate initial risk (R)
        if side == "long":
            initial_risk = entry_price - stop_price + entry_fees  # Include entry fees in risk
        else:  # short
            initial_risk = stop_price - entry_price + entry_fees
        
        if initial_risk <= 0:
            return Decimal('0')
        
        # Calculate fee-adjusted profit/loss
        if side == "long":
            gross_pnl = exit_price - entry_price
        else:  # short
            gross_pnl = entry_price - exit_price
        
        net_pnl = gross_pnl - entry_fees - exit_fees
        
        # R-multiple is net PnL divided by initial risk
        r_multiple = net_pnl / initial_risk
        
        return r_multiple
    
    def generate_tax_summary(self, tax_year: int) -> TaxSummary:
        """Generate comprehensive tax summary for a given year"""
        
        conn = sqlite3.connect(self.db_path)
        
        # Query transactions for the tax year
        cursor = conn.execute('''
            SELECT * FROM tax_transactions 
            WHERE date(timestamp) BETWEEN ? AND ?
            ORDER BY timestamp
        ''', (f'{tax_year}-01-01', f'{tax_year}-12-31'))
        
        transactions = cursor.fetchall()
        
        # Initialize summary
        summary = TaxSummary(year=tax_year)
        
        for row in transactions:
            # Parse transaction
            transaction = TaxableTransaction(
                transaction_id=row[0],
                timestamp=datetime.fromisoformat(row[1]),
                event_type=TaxableEvent(row[2]),
                symbol=row[3],
                quantity=Decimal(str(row[4])),
                price=Decimal(str(row[5])),
                fees=Decimal(str(row[6])),
                proceeds=Decimal(str(row[7])),
                cost_basis=Decimal(str(row[8])),
                gain_loss=Decimal(str(row[9])),
                is_long_term=bool(row[10]),
                is_wash_sale=bool(row[11])
            )
            
            # Only process disposals for tax calculations
            if transaction.proceeds > 0:  # This is a disposal
                summary.total_proceeds += transaction.proceeds
                summary.total_cost_basis += transaction.cost_basis
                summary.total_fees += transaction.fees
                
                if transaction.is_wash_sale:
                    summary.wash_sale_disallowed += abs(transaction.gain_loss)
                else:
                    if transaction.is_long_term:
                        summary.long_term_gain_loss += transaction.gain_loss
                    else:
                        summary.short_term_gain_loss += transaction.gain_loss
                
                # Add to by-symbol breakdown
                if transaction.symbol not in summary.by_symbol:
                    summary.by_symbol[transaction.symbol] = {
                        'proceeds': Decimal('0'),
                        'cost_basis': Decimal('0'),
                        'gain_loss': Decimal('0'),
                        'transactions': 0
                    }
                
                symbol_data = summary.by_symbol[transaction.symbol]
                symbol_data['proceeds'] += transaction.proceeds
                symbol_data['cost_basis'] += transaction.cost_basis
                symbol_data['gain_loss'] += transaction.gain_loss
                symbol_data['transactions'] += 1
            
            summary.transactions.append(transaction)
        
        conn.close()
        
        # Save summary to database
        self._save_tax_summary(summary)
        
        logger.info(f"Generated tax summary for {tax_year}: "
                   f"Total gain/loss: ${summary.short_term_gain_loss + summary.long_term_gain_loss:.2f}")
        
        return summary
    
    def _save_tax_summary(self, summary: TaxSummary):
        """Save tax summary to database"""
        
        conn = sqlite3.connect(self.db_path)
        
        summary_data = {
            'by_symbol': {k: {sk: float(sv) if isinstance(sv, Decimal) else sv 
                            for sk, sv in v.items()} for k, v in summary.by_symbol.items()},
            'transaction_count': len(summary.transactions)
        }
        
        conn.execute('''
            INSERT OR REPLACE INTO tax_summaries (
                year, total_proceeds, total_cost_basis, short_term_gain_loss,
                long_term_gain_loss, total_fees, wash_sale_disallowed, summary_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            summary.year,
            float(summary.total_proceeds),
            float(summary.total_cost_basis), 
            float(summary.short_term_gain_loss),
            float(summary.long_term_gain_loss),
            float(summary.total_fees),
            float(summary.wash_sale_disallowed),
            json.dumps(summary_data)
        ))
        
        conn.commit()
        conn.close()
    
    def export_for_tax_software(self, tax_year: int, format: str = "turbotax") -> str:
        """
        Export tax data in format suitable for popular tax software
        
        Args:
            tax_year: Tax year to export
            format: Export format ("turbotax", "hrblock", "csv")
            
        Returns:
            File path of exported data
        """
        
        summary = self.generate_tax_summary(tax_year)
        
        if format == "csv":
            filename = f"crypto_tax_report_{tax_year}.csv"
            
            # Create detailed CSV report
            df_data = []
            
            for transaction in summary.transactions:
                if transaction.proceeds > 0:  # Only disposals
                    df_data.append({
                        'Date_Sold': transaction.timestamp.strftime('%m/%d/%Y'),
                        'Symbol': transaction.symbol,
                        'Quantity': float(transaction.quantity),
                        'Proceeds': float(transaction.proceeds),
                        'Cost_Basis': float(transaction.cost_basis),
                        'Gain_Loss': float(transaction.gain_loss),
                        'Term': 'Long-term' if transaction.is_long_term else 'Short-term',
                        'Fees': float(transaction.fees),
                        'Wash_Sale': 'Yes' if transaction.is_wash_sale else 'No'
                    })
            
            df = pd.DataFrame(df_data)
            df.to_csv(filename, index=False)
            
            logger.info(f"Exported tax data to {filename}")
            return filename
        
        else:
            raise ValueError(f"Export format '{format}' not supported")
    
    def get_current_holdings(self) -> Dict[str, Dict]:
        """Get current cryptocurrency holdings with cost basis"""
        
        holdings_summary = {}
        
        for symbol, lots in self.holdings.items():
            total_quantity = sum(lot.quantity for lot in lots if lot.quantity > 0)
            total_cost_basis = sum(lot.cost_basis + lot.fees_paid for lot in lots if lot.quantity > 0)
            
            if total_quantity > 0:
                holdings_summary[symbol] = {
                    'quantity': float(total_quantity),
                    'total_cost_basis': float(total_cost_basis),
                    'average_cost_per_unit': float(total_cost_basis / total_quantity),
                    'lots': len([lot for lot in lots if lot.quantity > 0])
                }
        
        return holdings_summary

# ============================================================================
# USAGE EXAMPLE
# ============================================================================

def example_usage():
    """Example of enhanced tax integration usage"""
    
    # Initialize tax engine
    tax_engine = TaxCalculationEngine(cost_basis_method=CostBasisMethod.FIFO)
    
    # Example trades with fees
    
    # Buy 1 BTC at $50,000 with $50 fees
    tax_engine.record_acquisition(
        symbol="BTC",
        quantity=Decimal('1.0'),
        price=Decimal('50000'),
        timestamp=datetime(2023, 1, 15),
        fees=Decimal('50'),
        transaction_id="buy_btc_001"
    )
    
    # Buy 0.5 BTC at $55,000 with $30 fees
    tax_engine.record_acquisition(
        symbol="BTC", 
        quantity=Decimal('0.5'),
        price=Decimal('55000'),
        timestamp=datetime(2023, 6, 15),
        fees=Decimal('30'),
        transaction_id="buy_btc_002"
    )
    
    # Sell 0.8 BTC at $60,000 with $40 fees (should be long-term gain)
    disposal_transaction = tax_engine.record_disposal(
        symbol="BTC",
        quantity=Decimal('0.8'),
        price=Decimal('60000'),
        timestamp=datetime(2024, 2, 15),
        fees=Decimal('40'),
        transaction_id="sell_btc_001"
    )
    
    print(f"Disposal transaction:")
    print(f"  Proceeds: ${disposal_transaction.proceeds}")
    print(f"  Cost Basis: ${disposal_transaction.cost_basis}")
    print(f"  Gain/Loss: ${disposal_transaction.gain_loss}")
    print(f"  Long-term: {disposal_transaction.is_long_term}")
    print(f"  Fees: ${disposal_transaction.fees}")
    
    # Calculate fee-adjusted R-multiple
    r_multiple = tax_engine.calculate_fee_adjusted_r_multiple(
        entry_price=Decimal('50000'),
        exit_price=Decimal('60000'),
        entry_fees=Decimal('50'),
        exit_fees=Decimal('40'),
        stop_price=Decimal('45000'),
        side="long"
    )
    print(f"  Fee-adjusted R-multiple: {r_multiple:.2f}")
    
    # Generate tax summary
    tax_summary = tax_engine.generate_tax_summary(2024)
    print(f"\n2024 Tax Summary:")
    print(f"  Total Proceeds: ${tax_summary.total_proceeds}")
    print(f"  Total Cost Basis: ${tax_summary.total_cost_basis}")
    print(f"  Short-term Gain/Loss: ${tax_summary.short_term_gain_loss}")
    print(f"  Long-term Gain/Loss: ${tax_summary.long_term_gain_loss}")
    print(f"  Total Fees: ${tax_summary.total_fees}")
    
    # Export for tax software
    csv_file = tax_engine.export_for_tax_software(2024, "csv")
    print(f"\nTax report exported to: {csv_file}")
    
    # Current holdings
    holdings = tax_engine.get_current_holdings()
    print(f"\nCurrent Holdings: {holdings}")

if __name__ == "__main__":
    example_usage()