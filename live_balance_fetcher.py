#!/usr/bin/env python3
"""
Live Portfolio Balance Fetcher
=============================
Fetches actual live portfolio balance from Binance.US and updates configuration
"""

import ccxt
import os
from typing import Dict, Any
from dotenv import load_dotenv

class LiveBalanceFetcher:
    """Fetches live portfolio balance from Binance.US"""
    
    def __init__(self):
        load_dotenv()
        self.exchange = ccxt.binanceus({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_API_SECRET'),
            'sandbox': False,  # LIVE MODE
            'enableRateLimit': True,
        })
    
    def fetch_live_portfolio_value(self) -> float:
        """Fetch current live portfolio value in USD"""
        try:
            balance = self.exchange.fetch_balance()
            
            total_value = 0.0
            holdings = {}
            
            for asset, amounts in balance.items():
                if asset != 'info' and isinstance(amounts, dict):
                    total = amounts.get('total', 0)
                    
                    if total > 0:
                        holdings[asset] = total
                        
                        if asset in ['USDT', 'USD', 'BUSD']:
                            # Stablecoins = direct USD value
                            usd_value = total
                        elif asset not in ['info']:
                            try:
                                # Get current price for other assets
                                ticker = self.exchange.fetch_ticker(f'{asset}/USDT')
                                usd_value = total * ticker['last']
                            except Exception as e:
                                # If we can't get price, skip this asset
                                print(f"⚠️ Could not get price for {asset}: {e}")
                                continue
                        
                        total_value += usd_value
            
            return round(total_value, 2)
            
        except Exception as e:
            print(f"❌ Error fetching live balance: {e}")
            raise
    
    def get_detailed_balance(self) -> Dict[str, any]:
        """Get detailed balance breakdown"""
        try:
            balance = self.exchange.fetch_balance()
            holdings = {}
            total_value = 0.0
            
            for asset, amounts in balance.items():
                if asset != 'info' and isinstance(amounts, dict):
                    total = amounts.get('total', 0)
                    free = amounts.get('free', 0)
                    used = amounts.get('used', 0)
                    
                    if total > 0:
                        if asset in ['USDT', 'USD', 'BUSD']:
                            usd_value = total
                            price = 1.0
                        else:
                            try:
                                ticker = self.exchange.fetch_ticker(f'{asset}/USDT')
                                price = ticker['last']
                                usd_value = total * price
                            except:
                                price = 0
                                usd_value = 0
                        
                        holdings[asset] = {
                            'total': total,
                            'free': free,
                            'used': used,
                            'price_usd': price,
                            'value_usd': usd_value
                        }
                        
                        total_value += usd_value
            
            return {
                'holdings': holdings,
                'total_value_usd': round(total_value, 2),
                'timestamp': self.exchange.milliseconds()
            }
            
        except Exception as e:
            print(f"❌ Error fetching detailed balance: {e}")
            raise

if __name__ == "__main__":
    # Test the live balance fetcher
    fetcher = LiveBalanceFetcher()
    
    try:
        balance_info = fetcher.get_detailed_balance()
        
        print("🏦 LIVE BINANCE.US PORTFOLIO:")
        print("=" * 40)
        
        for asset, info in balance_info['holdings'].items():
            print(f"{asset}: {info['total']:.8f} @ ${info['price_usd']:.4f} = ${info['value_usd']:.2f}")
        
        print(f"\n💰 TOTAL PORTFOLIO VALUE: ${balance_info['total_value_usd']}")
        
    except Exception as e:
        print(f"Failed to fetch live balance: {e}")