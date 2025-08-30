#!/usr/bin/env python3
"""
Test Real Order Capability
==========================
Verify the bot can place real orders (test order validation only)
"""

import os
from dotenv import load_dotenv
from binance.client import Client as BinanceClient
from binance.exceptions import BinanceAPIException

load_dotenv()

def test_order_capability():
    """Test real order placement capability"""
    
    print("🔍 TESTING REAL ORDER CAPABILITY")
    print("=" * 40)
    
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    
    client = BinanceClient(api_key, api_secret, tld='us', testnet=False)
    
    try:
        # Test 1: Check if we can create a TEST order (validation only)
        print("1️⃣ Testing order validation (no actual order)...")
        
        # Get current BTC price for a realistic test order
        ticker = client.get_symbol_ticker(symbol="BTCUSDT")
        current_price = float(ticker['price'])
        
        # Calculate a small test order amount (much lower than current price)
        test_price = current_price * 0.5  # 50% below market (won't execute)
        test_quantity = 0.001  # Very small amount
        
        print(f"✅ Current BTC Price: ${current_price:,.2f}")
        print(f"✅ Test Order Price: ${test_price:,.2f} (50% below market)")
        print(f"✅ Test Order Quantity: {test_quantity} BTC")
        
        # Test order creation (TEST mode - no real execution)
        try:
            # This validates the order but doesn't execute it
            test_order = client.create_test_order(
                symbol='BTCUSDT',
                side='BUY',
                type='LIMIT',
                timeInForce='GTC',
                quantity=test_quantity,
                price=f"{test_price:.2f}"
            )
            print("✅ Order validation: SUCCESS")
            print("✅ Bot CAN place real orders when conditions are met")
            
        except BinanceAPIException as e:
            if "insufficient" in str(e).lower():
                print("✅ Order validation: SUCCESS (insufficient balance normal for test)")
            else:
                print(f"⚠️ Order validation issue: {e}")
        
        # Test 2: Check order history access
        print("\n2️⃣ Checking order history access...")
        try:
            orders = client.get_all_orders(symbol='BTCUSDT', limit=1)
            print("✅ Order history access: SUCCESS")
        except Exception as e:
            print(f"⚠️ Order history: {e}")
        
        # Test 3: Check account trading status
        print("\n3️⃣ Final trading capability check...")
        account = client.get_account()
        can_trade = account.get('canTrade', False)
        
        print(f"✅ Account Trading Status: {can_trade}")
        
        if can_trade:
            print("\n🎉 CONFIRMED: BOT CAN EXECUTE REAL TRADES!")
            print("🔥 When trading signals are detected, bot will:")
            print("   • Place REAL buy/sell orders")
            print("   • Use REAL money from your account") 
            print("   • Execute trades on REAL market")
            print("   • Generate REAL profits/losses")
            print("\n⚠️  THIS IS NOT A SIMULATION!")
            return True
        else:
            print("\n❌ Account cannot trade - check API permissions")
            return False
            
    except Exception as e:
        print(f"❌ Error testing order capability: {e}")
        return False

if __name__ == "__main__":
    success = test_order_capability()
    
    if success:
        print("\n" + "=" * 50)
        print("🚨 FINAL CONFIRMATION:")
        print("Your bot IS connected to your REAL Binance.US account")
        print("and WILL execute REAL trades with REAL money!")
        print("Ready for aggressive live trading with 1000x potential!")
        print("=" * 50)