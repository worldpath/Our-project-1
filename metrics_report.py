#!/usr/bin/env python3
"""
Metrics and reporting module for crypto bot
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

def summary_metrics(trade_file: str) -> Dict[str, Any]:
    """Generate summary trading metrics"""
    try:
        if not Path(trade_file).exists():
            return {"error": "Trade file not found"}
            
        df = pd.read_csv(trade_file)
        if df.empty:
            return {"trades": 0, "pnl": 0, "win_rate": 0}
            
        # Basic metrics
        total_trades = len(df)
        
        # Calculate PnL if we have the right columns
        if 'pnl' in df.columns:
            total_pnl = df['pnl'].sum()
            winning_trades = (df['pnl'] > 0).sum()
            losing_trades = (df['pnl'] < 0).sum()
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        else:
            total_pnl = 0
            winning_trades = 0
            losing_trades = 0
            win_rate = 0
            
        # Recent performance (last 24h, 7d, 30d)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            now = datetime.now()
            
            day_ago = now - timedelta(days=1)
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)
            
            recent_24h = df[df['timestamp'] >= day_ago]
            recent_7d = df[df['timestamp'] >= week_ago]
            recent_30d = df[df['timestamp'] >= month_ago]
            
            metrics = {
                "total_trades": total_trades,
                "total_pnl": round(total_pnl, 2),
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": round(win_rate, 2),
                "trades_24h": len(recent_24h),
                "pnl_24h": round(recent_24h['pnl'].sum(), 2) if 'pnl' in recent_24h.columns else 0,
                "trades_7d": len(recent_7d),
                "pnl_7d": round(recent_7d['pnl'].sum(), 2) if 'pnl' in recent_7d.columns else 0,
                "trades_30d": len(recent_30d),
                "pnl_30d": round(recent_30d['pnl'].sum(), 2) if 'pnl' in recent_30d.columns else 0,
            }
        else:
            metrics = {
                "total_trades": total_trades,
                "total_pnl": round(total_pnl, 2),
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": round(win_rate, 2),
            }
            
        return metrics
        
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        return {"error": str(e)}

def equity_curve(trade_file: str) -> List[Dict[str, Any]]:
    """Generate equity curve data"""
    try:
        if not Path(trade_file).exists():
            return []
            
        df = pd.read_csv(trade_file)
        if df.empty or 'pnl' not in df.columns:
            return []
            
        # Sort by timestamp
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            
        # Calculate cumulative PnL
        df['cumulative_pnl'] = df['pnl'].cumsum()
        
        # Assuming starting equity of 10000
        starting_equity = 10000
        df['equity'] = starting_equity + df['cumulative_pnl']
        
        equity_data = []
        for _, row in df.iterrows():
            if 'timestamp' in row:
                timestamp = row['timestamp'].isoformat() if pd.notnull(row['timestamp']) else datetime.now().isoformat()
            else:
                timestamp = datetime.now().isoformat()
                
            equity_data.append({
                't': timestamp,
                'equity': round(row['equity'], 2)
            })
            
        return equity_data
        
    except Exception as e:
        logger.error(f"Error generating equity curve: {e}")
        return []