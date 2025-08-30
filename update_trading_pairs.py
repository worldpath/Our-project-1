#!/usr/bin/env python3
"""
Update trading bot configuration to include all available Binance.US crypto/USDT pairs
"""
import json
import re

def load_all_pairs():
    """Load all available pairs from the analysis"""
    with open('/home/user/webapp/all_binance_usdt_pairs.json', 'r') as f:
        data = json.load(f)
    return data['all_pairs']

def categorize_pairs(all_pairs):
    """Categorize pairs by tier for risk management"""
    
    # Tier 1: Major cryptocurrencies (highest priority)
    tier1_major = [
        "BTC/USDT", "ETH/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", 
        "SOL/USDT", "AVAX/USDT", "DOT/USDT", "LINK/USDT", "LTC/USDT",
        "BCH/USDT", "ATOM/USDT", "NEAR/USDT", "UNI/USDT", "ALGO/USDT"
    ]
    
    # Tier 2: Established altcoins (medium priority)
    tier2_established = [
        "DOGE/USDT", "SHIB/USDT", "MATIC/USDT", "CRV/USDT", "AAVE/USDT",
        "COMP/USDT", "MKR/USDT", "SNX/USDT", "1INCH/USDT", "SUSHI/USDT",
        "FIL/USDT", "VET/USDT", "ICP/USDT", "THETA/USDT", "EOS/USDT",
        "XTZ/USDT", "ZEC/USDT", "DASH/USDT", "ETC/USDT", "NEO/USDT",
        "QTUM/USDT", "ZRX/USDT", "BAT/USDT", "ENJ/USDT", "MANA/USDT",
        "SAND/USDT", "AXS/USDT", "APE/USDT", "GALA/USDT", "CHZ/USDT"
    ]
    
    # Tier 3: All remaining pairs (lower priority but still tradeable)
    tier3_others = [pair for pair in all_pairs if pair not in tier1_major and pair not in tier2_established]
    
    # Filter out obvious meme/risky coins for tier 1&2 (keep them in tier 3)
    high_risk_keywords = ['MOG', 'REKT', 'FART', 'NOBODY', 'USELESS', 'TOSHI']
    tier3_others = [pair for pair in tier3_others if not any(keyword in pair for keyword in high_risk_keywords)]
    
    # Add the filtered high risk ones back
    tier3_meme = [pair for pair in all_pairs if any(keyword in pair for keyword in high_risk_keywords)]
    
    return {
        'tier1_major': [p for p in tier1_major if p in all_pairs],
        'tier2_established': [p for p in tier2_established if p in all_pairs], 
        'tier3_others': tier3_others,
        'tier3_meme': tier3_meme
    }

def update_main_py():
    """Update the main.py file with expanded trading pairs"""
    
    # Load all pairs
    all_pairs = load_all_pairs()
    categorized = categorize_pairs(all_pairs)
    
    print(f"📊 Categorized pairs:")
    print(f"  Tier 1 (Major): {len(categorized['tier1_major'])} pairs")
    print(f"  Tier 2 (Established): {len(categorized['tier2_established'])} pairs")
    print(f"  Tier 3 (Others): {len(categorized['tier3_others'])} pairs") 
    print(f"  Tier 3 (Meme): {len(categorized['tier3_meme'])} pairs")
    print(f"  Total: {sum(len(v) for v in categorized.values())} pairs")
    
    # Read current main.py
    with open('/home/user/webapp/main.py', 'r') as f:
        content = f.read()
    
    # Create the new trading pairs configuration
    new_pairs_config = f'''    def __post_init__(self):
        if self.trading_pairs is None:
            # EXPANDED CONFIGURATION: All {len(all_pairs)} available Binance.US crypto/USDT pairs
            # Categorized by risk/volume for strategic trading
            
            # Tier 1: Major cryptocurrencies (15 pairs) - Highest priority
            tier1_major = {repr(categorized['tier1_major'])}
            
            # Tier 2: Established altcoins ({len(categorized['tier2_established'])} pairs) - Medium priority  
            tier2_established = {repr(categorized['tier2_established'])}
            
            # Tier 3: Additional opportunities ({len(categorized['tier3_others'])} pairs) - Lower priority
            tier3_others = {repr(categorized['tier3_others'])}
            
            # Tier 3: High-risk/Meme coins ({len(categorized['tier3_meme'])} pairs) - Aggressive only
            tier3_meme = {repr(categorized['tier3_meme'])}
            
            # Combine all tiers for maximum trading opportunities
            if self.trading_mode == "conservative":
                self.trading_pairs = tier1_major[:10]  # Conservative: Top 10 major pairs
            elif self.trading_mode == "moderate":
                self.trading_pairs = tier1_major + tier2_established[:15]  # Moderate: Major + some established
            else:  # aggressive mode - USE ALL PAIRS FOR 1000x POTENTIAL
                self.trading_pairs = tier1_major + tier2_established + tier3_others + tier3_meme
            
            print(f"🚀 {{self.trading_mode.upper()}} MODE: Trading {{len(self.trading_pairs)}} pairs out of {len(all_pairs)} available")
            print(f"📈 EXPANSION: From 10 pairs to {{len(self.trading_pairs)}} pairs ({{\
(len(self.trading_pairs)/10)*100:.0f}}% increase in opportunities)")'''
    
    # Replace the old __post_init__ method
    pattern = r'    def __post_init__\(self\):.*?(?=\n\n@dataclass|\n\nclass|\nclass|\Z)'
    replacement = new_pairs_config
    
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Write updated content
    with open('/home/user/webapp/main.py', 'w') as f:
        f.write(new_content)
    
    print(f"\n✅ Updated main.py with all {len(all_pairs)} available trading pairs")
    print(f"🎯 AGGRESSIVE MODE will now trade ALL {len(all_pairs)} pairs for maximum 1000x potential!")
    
    return categorized

def update_config_yaml():
    """Update the aggressive config YAML with expanded pairs"""
    
    all_pairs = load_all_pairs()
    
    config_content = f"""# AGGRESSIVE PRODUCTION CONFIGURATION - MAXIMUM 1000x POTENTIAL
# ALL {len(all_pairs)} AVAILABLE BINANCE.US CRYPTO/USDT PAIRS

trading:
  mode: "aggressive"
  environment: "production" 
  
  # MAXIMUM AGGRESSIVE RISK SETTINGS FOR 1000x GAINS
  portfolio_risk: 80.0              # 80% portfolio at risk
  max_position_size: 50.0           # 50% in single position
  concurrent_positions: 12          # Up to 12 positions simultaneously
  risk_per_trade: 15.0              # 15% risk per trade
  
  # ALL AVAILABLE TRADING PAIRS ({len(all_pairs)} pairs)
  trading_pairs: {repr(all_pairs)}
  
  # Aggressive timing
  timeframe: "15m"                  # 15-minute cycles for rapid opportunities
  signal_threshold: 0.3             # Lower threshold = more trades
  
risk_management:
  max_daily_loss: 12.0              # 12% daily loss limit
  max_drawdown: 35.0                # 35% maximum drawdown
  emergency_stop: 40.0              # 40% emergency portfolio stop
  
features:
  live_trading: true
  automated_trading: true
  operation_24_7: true
  daily_reports: true
  email_notifications: true
  
portfolio:
  rebalancing: true
  auto_compound: true
  target_allocation: "dynamic"       # Dynamic allocation across all pairs
"""

    with open('/home/user/webapp/config/aggressive_production.yaml', 'w') as f:
        f.write(config_content)
    
    print(f"✅ Updated aggressive_production.yaml with all {len(all_pairs)} trading pairs")

def main():
    print("🔧 Updating trading bot configuration with ALL available Binance.US pairs...")
    
    # Update main.py
    categorized = update_main_py()
    
    # Update config YAML
    update_config_yaml()
    
    # Summary
    all_pairs = load_all_pairs()
    print(f"\n🎯 CONFIGURATION UPDATED:")
    print(f"  📊 Total available pairs: {len(all_pairs)}")
    print(f"  🚀 Aggressive mode pairs: {len(all_pairs)} (ALL PAIRS)")
    print(f"  📈 Opportunity expansion: {len(all_pairs)/10*100:.0f}% increase")
    print(f"  💰 1000x potential: MAXIMIZED across ALL markets")
    print(f"\n⚡ The bot will now scan and trade ALL {len(all_pairs)} crypto/USDT pairs!")
    print(f"🎪 Including trending coins like: PEPE, BONK, WIF, TRUMP, PENGU, HYPE, and more!")

if __name__ == "__main__":
    main()