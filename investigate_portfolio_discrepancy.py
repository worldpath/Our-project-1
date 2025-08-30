#!/usr/bin/env python3
"""
Investigate Portfolio Value Discrepancy
=====================================
Real Portfolio: $3,804.32
Bot Showing: $344.27
Need to find why there's a $3,460 difference!
"""

import os
from dotenv import load_dotenv
from binance.client import Client as BinanceClient
import requests

load_dotenv()

def investigate_portfolio_discrepancy():
    """Investigate the portfolio value discrepancy"""
    
    print("🔍 INVESTIGATING PORTFOLIO VALUE DISCREPANCY")
    print("=" * 50)
    print(f"🎯 Real Portfolio Value: $3,804.32")
    print(f"🤖 Bot Showing: $344.27")
    print(f"❓ Discrepancy: ${3804.32 - 344.27:,.2f}")
    print()
    
    # Get API credentials
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    
    client = BinanceClient(api_key, api_secret, tld='us', testnet=False)
    
    try:
        # 1. Get ALL account balances with current prices
        print("1️⃣ DETAILED ACCOUNT BALANCE ANALYSIS:")
        print("-" * 40)
        
        account = client.get_account()
        balances = account.get('balances', [])
        
        total_usd_value = 0
        significant_holdings = []
        
        print("Asset Holdings:")
        for balance in balances:
            free = float(balance['free'])
            locked = float(balance['locked'])
            total = free + locked
            
            if total > 0:
                asset = balance['asset']
                
                # Get current USD value for each asset
                if asset in ['USD', 'USDT', 'USDC', 'BUSD']:
                    usd_value = total
                    price = 1.0
                else:
                    try:
                        # Get current price in USDT
                        if asset != 'USDT':
                            ticker = client.get_symbol_ticker(symbol=f"{asset}USDT")
                            price = float(ticker['price'])
                        else:
                            price = 1.0
                        usd_value = total * price
                    except:
                        # If can't get USDT price, try USD price
                        try:
                            ticker = client.get_symbol_ticker(symbol=f"{asset}USD")
                            price = float(ticker['price'])
                            usd_value = total * price
                        except:
                            price = 0
                            usd_value = 0
                
                if usd_value > 0:
                    significant_holdings.append({
                        'asset': asset,
                        'quantity': total,
                        'price': price,
                        'usd_value': usd_value
                    })
                    
                    print(f"  {asset}: {total:>12.8f} × ${price:>8.2f} = ${usd_value:>8.2f}")
                    total_usd_value += usd_value
        
        print("-" * 40)
        print(f"📊 TOTAL CALCULATED VALUE: ${total_usd_value:,.2f}")
        print()
        
        # 2. Check what the bot is seeing
        print("2️⃣ BOT'S CURRENT CALCULATION:")
        print("-" * 32)
        
        try:
            response = requests.get("http://localhost:8889/status")
            bot_data = response.json()
            bot_portfolio = bot_data['performance']['portfolio_value']
            print(f"Bot Portfolio Value: {bot_portfolio}")
            
            # Check how bot calculates this
            print("\nBot's balance calculation method:")
            print("- Bot only counts USD/USDT/USDC for trading")
            print("- Bot may not be valuing crypto holdings")
            
        except Exception as e:
            print(f"Error getting bot status: {e}")
        
        # 3. Analysis
        print("\n3️⃣ DISCREPANCY ANALYSIS:")
        print("-" * 25)
        
        usd_only = sum(h['usd_value'] for h in significant_holdings if h['asset'] in ['USD', 'USDT', 'USDC'])
        crypto_value = sum(h['usd_value'] for h in significant_holdings if h['asset'] not in ['USD', 'USDT', 'USDC'])
        
        print(f"💵 USD/Stablecoins Only: ${usd_only:,.2f}")
        print(f"🪙 Crypto Holdings Value: ${crypto_value:,.2f}")
        print(f"📊 Total Portfolio: ${total_usd_value:,.2f}")
        print()
        
        if abs(usd_only - 344.27) < 1:
            print("🎯 FOUND THE ISSUE!")
            print("The bot is only counting USD/stablecoins for trading.")
            print("It's ignoring the value of your crypto holdings!")
            print()
            print(f"Bot sees: ${usd_only:,.2f} (USD only)")
            print(f"Reality: ${total_usd_value:,.2f} (Total portfolio)")
            print(f"Missing: ${crypto_value:,.2f} (Crypto holdings)")
        
        # 4. Impact on trading amounts
        print("\n4️⃣ TRADING AMOUNT IMPACT:")
        print("-" * 26)
        
        current_per_trade = usd_only * 0.5  # 50% position size
        correct_per_trade = total_usd_value * 0.5
        
        print(f"Current per trade (wrong): ${current_per_trade:,.2f}")
        print(f"Should be per trade: ${correct_per_trade:,.2f}")
        print(f"Difference: ${correct_per_trade - current_per_trade:,.2f}")
        
        return {
            'total_portfolio': total_usd_value,
            'usd_only': usd_only,
            'crypto_value': crypto_value,
            'holdings': significant_holdings
        }
        
    except Exception as e:
        print(f"❌ Error investigating: {e}")
        return None

if __name__ == "__main__":
    result = investigate_portfolio_discrepancy()
    
    if result:
        print("\n" + "=" * 50)
        print("🔧 SOLUTION NEEDED:")
        print("Fix bot to include crypto holdings in portfolio calculation")
        print(f"Target Portfolio Value: ${result['total_portfolio']:,.2f}")
        print(f"Target Per Trade: ${result['total_portfolio'] * 0.5:,.2f}")
        print("=" * 50)