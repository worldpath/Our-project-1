#!/usr/bin/env python3
"""
Fix Trading Pairs Format
========================
Convert trading pairs to the expected format for the enhanced bot
"""

import json

def fix_trading_pairs():
    """Convert trading pairs to expected format"""
    
    # Read current file
    with open('all_binance_usdt_pairs.json', 'r') as f:
        data = json.load(f)
    
    # Get all pairs
    if 'all_pairs' in data:
        all_pairs = data['all_pairs']
    elif 'current_pairs' in data:
        all_pairs = data['current_pairs']
    else:
        print("❌ No pairs found in file")
        return
    
    # Convert to expected format
    formatted_pairs = []
    for pair in all_pairs:
        # Convert from "BTC/USDT" to "BTCUSDT" format
        symbol = pair.replace('/', '')
        formatted_pairs.append({
            'symbol': symbol,
            'baseAsset': symbol.replace('USDT', ''),
            'quoteAsset': 'USDT',
            'status': 'TRADING'
        })
    
    # Write back in correct format
    with open('all_binance_usdt_pairs.json', 'w') as f:
        json.dump(formatted_pairs, f, indent=2)
    
    print(f"✅ Fixed {len(formatted_pairs)} trading pairs")
    
    # Show first few pairs
    print("📊 Sample pairs:")
    for pair in formatted_pairs[:5]:
        print(f"  • {pair['symbol']}")

if __name__ == "__main__":
    fix_trading_pairs()