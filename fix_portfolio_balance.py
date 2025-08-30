#!/usr/bin/env python3
"""
Fix Portfolio Balance - Workaround for IP Whitelist Issues
========================================================
This script modifies the main bot to handle IP whitelist restrictions gracefully
and allows setting a realistic portfolio value for development/testing.
"""

import re
import os
from pathlib import Path

def fix_portfolio_initialization():
    """Fix the portfolio value initialization in main.py"""
    
    main_py_path = Path("main.py")
    if not main_py_path.exists():
        print("❌ main.py not found")
        return False
    
    # Read current main.py
    content = main_py_path.read_text()
    
    # Find the portfolio initialization line
    old_line = "        self.portfolio_value = float(os.getenv('INITIAL_CAPITAL', '10000'))"
    
    # New implementation with Binance API fallback
    new_code = '''        # Initialize portfolio value - try to get real balance first
        try:
            # Attempt to get real account balance
            import asyncio
            real_balances = asyncio.run(self.binance.get_account_balance())
            
            # Calculate total USD value from real account
            total_usd = 0
            for asset, balance_info in real_balances.items():
                if asset in ['USD', 'USDT', 'USDC', 'BUSD']:
                    total_usd += balance_info['total']
            
            if total_usd > 0:
                self.portfolio_value = total_usd
                print(f"✅ Using real account balance: ${total_usd:,.2f}")
            else:
                # Fallback to environment variable or default
                self.portfolio_value = float(os.getenv('REAL_PORTFOLIO_VALUE', os.getenv('INITIAL_CAPITAL', '10000')))
                print(f"⚠️ No USD balance found, using configured value: ${self.portfolio_value:,.2f}")
                
        except Exception as e:
            # Fallback for IP whitelist or other API issues
            self.portfolio_value = float(os.getenv('REAL_PORTFOLIO_VALUE', os.getenv('INITIAL_CAPITAL', '10000')))
            print(f"⚠️ Cannot access Binance API (IP whitelist?): {str(e)}")
            print(f"📊 Using configured portfolio value: ${self.portfolio_value:,.2f}")
            if "35.197.15.230" in str(e) or "IP" in str(e).upper():
                print(f"💡 TIP: Add IP 35.197.15.230 to your Binance.US API whitelist for live data")'''
    
    # Replace the line
    if old_line in content:
        content = content.replace(old_line, new_code)
        
        # Write back to file
        main_py_path.write_text(content)
        print("✅ Successfully updated main.py portfolio initialization")
        return True
    else:
        print("❌ Could not find portfolio initialization line to replace")
        print("Looking for:", old_line)
        return False

def update_environment_variables(real_balance=None):
    """Update .env file with realistic portfolio value"""
    
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env file not found")
        return False
    
    content = env_path.read_text()
    
    # Add REAL_PORTFOLIO_VALUE if not exists
    if "REAL_PORTFOLIO_VALUE" not in content:
        # Use default balance for automated setup
        if real_balance is None:
            real_balance = 25000  # Reasonable default for development
            print(f"   Using development default: ${real_balance:,.2f}")
            print("   (You can change REAL_PORTFOLIO_VALUE in .env file later)")
        
        # Add to .env file
        content += f"\n\n# Real portfolio value for development/testing\nREAL_PORTFOLIO_VALUE={real_balance}\n"
        env_path.write_text(content)
        print(f"✅ Added REAL_PORTFOLIO_VALUE=${real_balance:,.2f} to .env")
        return True
    else:
        print("✅ REAL_PORTFOLIO_VALUE already exists in .env")
        return True

def main():
    """Main function to fix portfolio balance issues"""
    
    print("🔧 Fixing Portfolio Balance for IP Whitelist Issues")
    print("=" * 55)
    
    # Get current IP
    try:
        import requests
        current_ip = requests.get("https://api.ipify.org", timeout=5).text.strip()
        print(f"📍 Current IP: {current_ip}")
    except:
        print("📍 Current IP: Unable to determine")
    
    print("🎯 Required IP: 207.246.99.108 (for Binance.US API)")
    print()
    
    # Fix main.py
    print("1️⃣ Updating main.py portfolio initialization...")
    if fix_portfolio_initialization():
        print("   ✅ main.py updated successfully")
    else:
        print("   ❌ Failed to update main.py")
        return False
    
    print()
    
    # Update environment
    print("2️⃣ Setting up realistic portfolio value...")
    if update_environment_variables():
        print("   ✅ Environment updated successfully")
    else:
        print("   ❌ Failed to update environment")
        return False
    
    print()
    print("🎉 Portfolio balance fix completed!")
    print()
    print("📋 Next Steps:")
    print("   1. Restart the trading bot to apply changes")
    print("   2. Check dashboard for realistic portfolio values")
    print("   3. For live API access: Add current IP to Binance.US whitelist")
    print()
    
    return True

if __name__ == "__main__":
    main()