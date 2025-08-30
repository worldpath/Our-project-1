#!/usr/bin/env python3
"""
Test Binance.US API Connection
=============================
Test script to verify API credentials and fetch real account balance
"""

import os
import sys
from dotenv import load_dotenv
from binance.client import Client as BinanceClient
from binance.exceptions import BinanceAPIException

# Load environment variables
load_dotenv()

def test_binance_connection():
    """Test Binance.US API connection and fetch account balance"""
    
    # Get API credentials from environment
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    
    print("🔍 Testing Binance.US API Connection...")
    print("=" * 50)
    
    # Check if credentials exist
    if not api_key or not api_secret:
        print("❌ ERROR: Missing API credentials")
        print(f"API Key: {'✅ Found' if api_key else '❌ Missing'}")
        print(f"API Secret: {'✅ Found' if api_secret else '❌ Missing'}")
        return False
    
    print(f"✅ API Key: {api_key[:10]}...{api_key[-4:]}")
    print(f"✅ API Secret: {api_secret[:10]}...{api_secret[-4:]}")
    print()
    
    try:
        # Initialize Binance.US client
        print("🔗 Initializing Binance.US client...")
        client = BinanceClient(api_key, api_secret, tld='us', testnet=False)
        
        # Test connection with server time
        print("⏰ Testing server connection...")
        server_time = client.get_server_time()
        print(f"✅ Server time: {server_time}")
        print()
        
        # Test API key permissions
        print("🔐 Testing API key permissions...")
        account_status = client.get_account_status()
        print(f"✅ Account status: {account_status}")
        print()
        
        # Get account information
        print("📊 Fetching account information...")
        account = client.get_account()
        
        print("✅ Account details:")
        print(f"   Account Type: {account.get('accountType', 'N/A')}")
        print(f"   Can Trade: {account.get('canTrade', 'N/A')}")
        print(f"   Can Withdraw: {account.get('canWithdraw', 'N/A')}")
        print(f"   Can Deposit: {account.get('canDeposit', 'N/A')}")
        print()
        
        # Get account balances
        print("💰 Account Balances:")
        print("-" * 30)
        balances = account.get('balances', [])
        total_usd_value = 0
        significant_balances = []
        
        for balance in balances:
            free = float(balance['free'])
            locked = float(balance['locked'])
            total = free + locked
            
            if total > 0:
                asset = balance['asset']
                significant_balances.append({
                    'asset': asset,
                    'free': free,
                    'locked': locked,
                    'total': total
                })
                print(f"   {asset}: {total:.8f} (Free: {free:.8f}, Locked: {locked:.8f})")
                
                # Estimate USD value for major coins
                if asset == 'USD' or asset == 'USDT' or asset == 'USDC':
                    total_usd_value += total
        
        print()
        if significant_balances:
            print(f"📈 Total estimated USD value: ${total_usd_value:,.2f}")
            print(f"🎯 Found {len(significant_balances)} assets with balance")
        else:
            print("⚠️ No significant balances found")
        
        print()
        print("🎉 SUCCESS: Binance.US API connection working!")
        return True, significant_balances, total_usd_value
        
    except BinanceAPIException as e:
        print(f"❌ Binance API Error: {e}")
        print(f"   Error Code: {e.code}")
        print(f"   Error Message: {e.message}")
        return False, [], 0
        
    except Exception as e:
        print(f"❌ General Error: {e}")
        return False, [], 0

if __name__ == "__main__":
    success, balances, usd_value = test_binance_connection()
    
    if success and usd_value > 0:
        print("\n" + "=" * 50)
        print("🚀 READY FOR LIVE TRADING!")
        print(f"💰 Portfolio Value: ${usd_value:,.2f}")
        print("=" * 50)
        sys.exit(0)
    else:
        print("\n" + "=" * 50)
        print("⚠️ API CONNECTION ISSUES DETECTED")
        print("Please check your API credentials and permissions")
        print("=" * 50)
        sys.exit(1)