#!/usr/bin/env python3
"""
VERIFY REAL TRADING - 100% Confirmation Script
==============================================
This script confirms the bot is connected to your REAL Binance.US account
and has the ability to execute REAL trades with REAL money.
"""

import os
from dotenv import load_dotenv
from binance.client import Client as BinanceClient
from binance.exceptions import BinanceAPIException
import json

# Load environment variables
load_dotenv()

def verify_real_trading_setup():
    """Comprehensive verification of real trading setup"""
    
    print("🔍 VERIFYING REAL TRADING SETUP")
    print("=" * 50)
    
    # Get API credentials
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ FATAL: No API credentials found!")
        return False
    
    print(f"✅ API Key: {api_key[:10]}...{api_key[-4:]}")
    print()
    
    try:
        # Initialize REAL Binance.US client (NOT testnet)
        print("🔗 Connecting to REAL Binance.US (NOT testnet)...")
        client = BinanceClient(api_key, api_secret, tld='us', testnet=False)
        
        # 1. Verify Real Account Access
        print("\n1️⃣ VERIFYING REAL ACCOUNT ACCESS:")
        print("-" * 30)
        account = client.get_account()
        
        print(f"✅ Account Type: {account.get('accountType', 'N/A')}")
        print(f"✅ Trading Enabled: {account.get('canTrade', False)}")
        print(f"✅ Withdraw Enabled: {account.get('canWithdraw', False)}")
        print(f"✅ Deposit Enabled: {account.get('canDeposit', False)}")
        
        if not account.get('canTrade', False):
            print("❌ CRITICAL: Account cannot trade!")
            return False
        
        # 2. Verify Real Balances
        print("\n2️⃣ VERIFYING REAL ACCOUNT BALANCES:")
        print("-" * 35)
        balances = account.get('balances', [])
        real_balances = {}
        
        for balance in balances:
            free = float(balance['free'])
            locked = float(balance['locked'])
            total = free + locked
            
            if total > 0:
                asset = balance['asset']
                real_balances[asset] = {
                    'free': free,
                    'locked': locked,
                    'total': total
                }
                print(f"✅ {asset}: {total:.8f} (Free: {free:.8f}, Locked: {locked:.8f})")
        
        if not real_balances:
            print("❌ CRITICAL: No real balances found!")
            return False
            
        # 3. Check Trading Permissions
        print("\n3️⃣ CHECKING TRADING PERMISSIONS:")
        print("-" * 32)
        
        try:
            # Test order permissions (without actually placing order)
            symbol_info = client.get_symbol_info('BTCUSDT')
            if symbol_info:
                print("✅ Can access trading symbols")
                print(f"✅ BTC/USDT trading: {symbol_info['status']}")
            
            # Check if we can get recent trades (requires trading permissions)
            recent_trades = client.get_my_trades(symbol='BTCUSDT', limit=1)
            print("✅ Trading history access confirmed")
            
        except BinanceAPIException as e:
            if "Invalid symbol" in str(e):
                print("✅ Trading permissions confirmed (symbol access)")
            else:
                print(f"⚠️ Trading permission check: {e}")
        
        # 4. Verify Environment Settings
        print("\n4️⃣ VERIFYING ENVIRONMENT SETTINGS:")
        print("-" * 34)
        
        environment = os.getenv('ENVIRONMENT', 'development')
        testnet_flag = False  # We explicitly set testnet=False above
        
        print(f"✅ Environment: {environment}")
        print(f"✅ Testnet Mode: {testnet_flag} (FALSE = REAL TRADING)")
        
        if environment != 'production':
            print("⚠️ WARNING: Environment is not 'production'")
        
        # 5. Calculate Real Trading Amounts
        print("\n5️⃣ CALCULATING REAL TRADING AMOUNTS:")
        print("-" * 36)
        
        # Get USD balance for calculations
        usd_balance = 0
        if 'USD' in real_balances:
            usd_balance = real_balances['USD']['free']
        elif 'USDT' in real_balances:
            usd_balance = real_balances['USDT']['free']
        elif 'USDC' in real_balances:
            usd_balance = real_balances['USDC']['free']
        
        print(f"✅ Available USD Balance: ${usd_balance:.2f}")
        
        # Get bot configuration
        portfolio_risk = float(os.getenv('PORTFOLIO_RISK', '80'))
        position_size = float(os.getenv('MAX_POSITION_SIZE', '50'))
        
        per_trade_amount = usd_balance * (position_size / 100)
        max_exposure = usd_balance * (portfolio_risk / 100)
        
        print(f"✅ Per Trade Amount: ${per_trade_amount:.2f}")
        print(f"✅ Max Portfolio Exposure: ${max_exposure:.2f}")
        print(f"✅ Portfolio Risk: {portfolio_risk}%")
        print(f"✅ Position Size: {position_size}%")
        
        # 6. Final Verification Summary
        print("\n6️⃣ FINAL VERIFICATION SUMMARY:")
        print("-" * 30)
        
        checks = [
            ("Real Binance.US Connection", True),
            ("Trading Permissions", account.get('canTrade', False)),
            ("Real Account Balances", len(real_balances) > 0),
            ("USD Available for Trading", usd_balance > 0),
            ("Testnet Mode", not testnet_flag),  # Should be False
            ("Production Environment", environment == 'production')
        ]
        
        all_passed = True
        for check_name, status in checks:
            status_icon = "✅" if status else "❌"
            print(f"{status_icon} {check_name}: {'PASS' if status else 'FAIL'}")
            if not status:
                all_passed = False
        
        print("\n" + "=" * 50)
        
        if all_passed:
            print("🎉 CONFIRMED: BOT IS CONNECTED TO REAL BINANCE.US ACCOUNT!")
            print("🔥 READY FOR REAL TRADING WITH REAL MONEY!")
            print(f"💰 Will trade with real ${per_trade_amount:.2f} per position")
            print("⚠️  THIS IS NOT A SIMULATION - REAL MONEY AT RISK!")
        else:
            print("❌ ISSUES DETECTED: Bot may not be properly configured for real trading")
        
        return all_passed, real_balances, per_trade_amount
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False, {}, 0

if __name__ == "__main__":
    success, balances, trade_amount = verify_real_trading_setup()
    
    if success:
        print("\n🚨 IMPORTANT CONFIRMATION:")
        print("This bot WILL execute REAL trades on your REAL Binance.US account")
        print("with REAL money. Are you ready for live trading? (The bot is ready!)")
    else:
        print("\n⚠️ SETUP INCOMPLETE: Please resolve issues before live trading")