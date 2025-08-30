#!/usr/bin/env python3
"""
Fetch all available Binance.US trading pairs and identify crypto/USDT pairs
"""
import requests
import json
from typing import List, Dict
import sys

def fetch_binance_us_pairs() -> List[Dict]:
    """Fetch all available trading pairs from Binance.US API"""
    try:
        url = "https://api.binance.us/api/v3/exchangeInfo"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        symbols = data.get('symbols', [])
        
        print(f"✅ Fetched {len(symbols)} total trading pairs from Binance.US")
        return symbols
        
    except Exception as e:
        print(f"❌ Error fetching Binance.US pairs: {e}")
        return []

def filter_usdt_pairs(symbols: List[Dict]) -> List[str]:
    """Filter for active crypto/USDT trading pairs"""
    usdt_pairs = []
    
    for symbol in symbols:
        # Check if it's a USDT pair and is actively trading
        if (symbol.get('quoteAsset') == 'USDT' and 
            symbol.get('status') == 'TRADING' and
            symbol.get('isSpotTradingAllowed', False)):
            
            base_asset = symbol.get('baseAsset', '')
            pair_name = f"{base_asset}/USDT"
            
            # Skip stablecoins and test pairs
            skip_assets = {'USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'USDP', 'TEST'}
            if base_asset not in skip_assets and not base_asset.endswith('USD'):
                usdt_pairs.append(pair_name)
    
    return sorted(usdt_pairs)

def analyze_pairs_volume(symbols: List[Dict]) -> List[Dict]:
    """Analyze volume and get pair details for USDT pairs"""
    pair_details = []
    
    for symbol in symbols:
        if (symbol.get('quoteAsset') == 'USDT' and 
            symbol.get('status') == 'TRADING' and
            symbol.get('isSpotTradingAllowed', False)):
            
            base_asset = symbol.get('baseAsset', '')
            
            # Skip stablecoins
            skip_assets = {'USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'USDP', 'TEST'}
            if base_asset not in skip_assets and not base_asset.endswith('USD'):
                pair_details.append({
                    'pair': f"{base_asset}/USDT",
                    'symbol': symbol.get('symbol', ''),
                    'baseAsset': base_asset,
                    'minQty': float(symbol.get('filters', [{}])[1].get('minQty', '0')) if len(symbol.get('filters', [])) > 1 else 0,
                    'tickSize': float(symbol.get('filters', [{}])[0].get('tickSize', '0')) if len(symbol.get('filters', [])) > 0 else 0
                })
    
    return pair_details

def main():
    print("🔍 Fetching all available Binance.US trading pairs...")
    
    # Fetch all pairs
    all_symbols = fetch_binance_us_pairs()
    if not all_symbols:
        print("❌ Failed to fetch trading pairs")
        sys.exit(1)
    
    # Filter USDT pairs
    usdt_pairs = filter_usdt_pairs(all_symbols)
    print(f"\n📊 Found {len(usdt_pairs)} active crypto/USDT pairs:")
    
    # Current hardcoded pairs
    current_pairs = [
        "BTC/USDT", "ETH/USDT", "ADA/USDT", "SOL/USDT", "MATIC/USDT",
        "XRP/USDT", "DOGE/USDT", "AVAX/USDT", "DOT/USDT", "LINK/USDT"
    ]
    
    print(f"\n🔄 Current bot pairs ({len(current_pairs)}):")
    for pair in current_pairs:
        status = "✅" if pair in usdt_pairs else "❌"
        print(f"  {status} {pair}")
    
    print(f"\n🆕 Additional available pairs ({len(usdt_pairs) - len(current_pairs)}):")
    additional_pairs = [pair for pair in usdt_pairs if pair not in current_pairs]
    for pair in additional_pairs:
        print(f"  ➕ {pair}")
    
    # Get detailed pair information
    pair_details = analyze_pairs_volume(all_symbols)
    
    # Save results to files
    with open('/home/user/webapp/all_binance_usdt_pairs.json', 'w') as f:
        json.dump({
            'total_pairs': len(usdt_pairs),
            'current_pairs': current_pairs,
            'all_pairs': usdt_pairs,
            'additional_pairs': additional_pairs,
            'pair_details': pair_details,
            'expansion_potential': f"{len(additional_pairs)} additional pairs available"
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: all_binance_usdt_pairs.json")
    print(f"\n📈 EXPANSION OPPORTUNITY:")
    print(f"  Current: {len(current_pairs)} pairs")
    print(f"  Available: {len(usdt_pairs)} pairs")
    print(f"  Potential increase: +{len(additional_pairs)} pairs ({((len(additional_pairs)/len(current_pairs))*100):.0f}% more opportunities)")
    
    return usdt_pairs, additional_pairs

if __name__ == "__main__":
    main()