#!/usr/bin/env python3
"""Quick API Test - Direct Binance.US Connection"""

import os
from dotenv import load_dotenv
from binance.client import Client as BinanceClient

load_dotenv()

api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')

print(f"🔑 API Key: {api_key[:10]}...{api_key[-4:]}")

try:
    client = BinanceClient(api_key, api_secret, tld='us')
    
    print("⏰ Testing server time...")
    server_time = client.get_server_time()
    print(f"✅ Server: {server_time}")
    
    print("\n🔍 Testing account access...")
    account = client.get_account()
    
    print(f"✅ Account Type: {account.get('accountType', 'N/A')}")
    print(f"✅ Can Trade: {account.get('canTrade', False)}")
    
    print(f"\n💰 Account Balances:")
    for balance in account.get('balances', [])[:5]:  # Show first 5
        free = float(balance['free'])
        locked = float(balance['locked'])
        if free > 0 or locked > 0:
            print(f"   {balance['asset']}: {free + locked}")
    
    print("\n🎉 SUCCESS! API CONNECTION WORKING!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print(f"Error type: {type(e).__name__}")
    
    # Try to get more specific error info
    if hasattr(e, 'response'):
        print(f"Response: {e.response}")
    if hasattr(e, 'status_code'):
        print(f"Status Code: {e.status_code}")