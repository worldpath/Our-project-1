#!/usr/bin/env python3
import yaml
import sys

config_file = "config/aggressive_production.yaml"

print(f"=== Checking {config_file} ===\n")

try:
    with open(config_file, 'r') as f:
        cfg = yaml.safe_load(f)
    
    print("✓ YAML file loaded successfully\n")
    
    # Check for required sections
    required = {
        'risk': ['risk_per_trade'],
        'portfolio': ['max_portfolio_heat', 'max_daily_loss', 'max_drawdown', 'concurrent_positions'],
        'strategy': ['enabled_strategies'],
        'reporting': ['trade_log_file'],
        'execution': ['order_type']
    }
    
    print("Checking required sections:\n")
    all_ok = True
    
    for section, keys in required.items():
        if section in cfg:
            print(f"✓ Section '{section}' exists")
            for key in keys:
                if key in cfg[section]:
                    print(f"  ✓ {section}.{key} = {cfg[section][key]}")
                else:
                    print(f"  ✗ {section}.{key} MISSING")
                    all_ok = False
        else:
            print(f"✗ Section '{section}' MISSING")
            all_ok = False
    
    print(f"\n{'='*50}")
    if all_ok:
        print("✓ Config structure is CORRECT")
    else:
        print("✗ Config structure has ERRORS")
        sys.exit(1)
        
except Exception as e:
    print(f"✗ Error loading YAML: {e}")
    sys.exit(1)
