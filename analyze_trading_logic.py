#!/usr/bin/env python3
"""
Analyze Trading Logic - Crypto Holdings vs Cash Trading
=====================================================
Check if the bot can:
1. Sell existing crypto holdings (BTC, SOL, ETH, etc.)
2. Rebalance between different cryptocurrencies  
3. Use full portfolio for optimal trading
OR
4. Only trades with available USD cash
"""

import os
import re
from pathlib import Path

def analyze_trading_logic():
    """Analyze the bot's trading logic capabilities"""
    
    print("🔍 ANALYZING TRADING LOGIC CAPABILITIES")
    print("=" * 50)
    
    print("📊 CURRENT PORTFOLIO BREAKDOWN:")
    print("- BTC: $2,634.40 (69% of portfolio)")
    print("- SOL: $455.66 (12% of portfolio)")  
    print("- ETH: $139.54 (4% of portfolio)")
    print("- USD: $344.27 (9% available cash)")
    print("- Others: $230+ (6%)")
    print()
    
    # Analyze main.py for trading logic
    main_py = Path("main.py")
    if not main_py.exists():
        print("❌ main.py not found")
        return
    
    content = main_py.read_text()
    
    print("1️⃣ CHECKING FOR SELL ORDER LOGIC:")
    print("-" * 35)
    
    # Look for sell functionality
    sell_patterns = [
        r"def.*sell",
        r"side.*=.*['\"]SELL['\"]",
        r"order_side.*=.*sell",
        r"client\.order_.*sell",
        r"create.*sell.*order"
    ]
    
    sell_found = False
    for pattern in sell_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            sell_found = True
            print(f"✅ Found sell logic: {matches[0]}")
    
    if not sell_found:
        print("❌ No sell order logic found")
    
    print("\n2️⃣ CHECKING FOR PORTFOLIO REBALANCING:")
    print("-" * 38)
    
    # Look for portfolio management
    rebalance_patterns = [
        r"rebalance",
        r"portfolio.*management", 
        r"existing.*positions",
        r"current.*holdings",
        r"asset.*allocation"
    ]
    
    rebalance_found = False
    for pattern in rebalance_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            rebalance_found = True
            print(f"✅ Found rebalancing logic: {matches[0]}")
    
    if not rebalance_found:
        print("❌ No portfolio rebalancing logic found")
    
    print("\n3️⃣ CHECKING ORDER EXECUTION METHOD:")
    print("-" * 34)
    
    # Look for how orders are executed
    order_patterns = [
        r"def.*execute.*order",
        r"def.*place.*order", 
        r"binance.*order",
        r"create.*order"
    ]
    
    for pattern in order_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            print(f"✅ Found order execution: {matches[0]}")
    
    print("\n4️⃣ CHECKING BALANCE USAGE:")
    print("-" * 26)
    
    # Look for how balances are used
    balance_patterns = [
        r"get.*balance",
        r"available.*balance",
        r"free.*balance",
        r"USD.*balance"
    ]
    
    for pattern in balance_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            print(f"✅ Found balance usage: {matches[0]}")
    
    print("\n5️⃣ ANALYZING TRADING STRATEGY:")
    print("-" * 30)
    
    # Check if it only uses USD or can trade crypto-to-crypto
    if "USD" in content and ("BTC" in content or "ETH" in content):
        print("✅ Bot references multiple assets (USD, BTC, ETH)")
    
    if "only.*USD" in content or "cash.*only" in content:
        print("⚠️ May be limited to USD trading only")
    
    # Look for specific trading logic
    if "market.*buy" in content and "market.*sell" not in content:
        print("⚠️ May only have buy logic, no sell logic")
    
    print("\n6️⃣ RECOMMENDATIONS:")
    print("-" * 18)
    
    if not sell_found:
        print("🔧 ISSUE: Bot likely only uses USD cash for trading")
        print("   - Cannot sell BTC ($2,634) to buy better opportunities")  
        print("   - Cannot sell SOL ($456) for different crypto")
        print("   - Limited to $344 USD cash only")
        print()
        print("💡 SOLUTION NEEDED:")
        print("   - Add sell logic for existing holdings")
        print("   - Enable crypto-to-crypto trading")
        print("   - Allow portfolio rebalancing")
        print()
        print("🎯 CURRENT LIMITATION:")
        print(f"   - Trading with: $344 USD (9% of portfolio)")
        print(f"   - Not using: $3,460 in crypto (91% of portfolio)")
    else:
        print("✅ Bot appears to have sell capabilities")
        print("✅ Can potentially trade full portfolio")
    
    return sell_found, rebalance_found

def check_binance_connector():
    """Check BinanceConnector class capabilities"""
    
    print("\n7️⃣ CHECKING BINANCE CONNECTOR:")
    print("-" * 31)
    
    main_py = Path("main.py")
    content = main_py.read_text()
    
    # Find BinanceConnector class
    connector_start = content.find("class BinanceConnector:")
    if connector_start == -1:
        print("❌ BinanceConnector class not found")
        return
    
    # Extract the class content (roughly)
    connector_end = content.find("\nclass ", connector_start + 1)
    if connector_end == -1:
        connector_end = len(content)
    
    connector_code = content[connector_start:connector_end]
    
    # Check for order methods
    if "def place_order" in connector_code:
        print("✅ Has place_order method")
    if "def buy_order" in connector_code:
        print("✅ Has buy_order method") 
    if "def sell_order" in connector_code:
        print("✅ Has sell_order method")
    else:
        print("❌ No sell_order method found")
    
    # Check for balance methods
    if "get_account_balance" in connector_code:
        print("✅ Has get_account_balance method")
    
    print("\n8️⃣ TRADING CAPACITY ANALYSIS:")
    print("-" * 30)
    
    print("Current Setup Analysis:")
    print(f"💵 Available USD: $344.27")
    print(f"🪙 Crypto Holdings: $3,460.05")
    print(f"📊 Total Portfolio: $3,804.32")
    print()
    
    if "sell_order" not in connector_code:
        print("⚠️ CRITICAL LIMITATION IDENTIFIED:")
        print("   Bot appears to be BUY-ONLY")
        print("   Cannot sell existing crypto holdings")
        print("   Trading limited to USD balance only")
        print()
        print("💰 IMPACT:")
        print(f"   - Usable for trading: $344.27 (9%)")
        print(f"   - Locked in holdings: $3,460.05 (91%)")
        print(f"   - Efficiency: Only using 9% of portfolio power")
    else:
        print("✅ Bot can potentially use full portfolio")

if __name__ == "__main__":
    sell_capable, rebalance_capable = analyze_trading_logic()
    check_binance_connector()
    
    print("\n" + "=" * 50)
    print("🎯 SUMMARY:")
    if not sell_capable:
        print("❌ Bot likely LIMITED to USD cash trading only")
        print("💡 Enhancement needed for full portfolio utilization")
    else:
        print("✅ Bot appears capable of full portfolio trading")
    print("=" * 50)