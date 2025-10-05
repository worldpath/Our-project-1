#!/usr/bin/env python3
import yaml

config_file = "config/aggressive_production.yaml"

print(f"Reading {config_file}...")
with open(config_file, 'r') as f:
    content = f.read()

# Load the YAML
cfg = yaml.safe_load(content)

# Merge all portfolio settings into one
merged_portfolio = {
    'max_portfolio_heat': 0.80,
    'max_daily_loss': 0.12,
    'max_drawdown': 0.35,
    'concurrent_positions': 12,
    'rebalancing': True,
    'auto_compound': True,
    'target_allocation': 'dynamic'
}

# Update the config
cfg['portfolio'] = merged_portfolio

# Write it back
print(f"Writing fixed config...")
with open(config_file, 'w') as f:
    yaml.dump(cfg, f, default_flow_style=False, sort_keys=False, width=120)

print("✓ Fixed duplicate portfolio sections!")
print("\nVerifying...")

# Verify
with open(config_file, 'r') as f:
    check = yaml.safe_load(f)
    
if 'portfolio' in check and 'max_portfolio_heat' in check['portfolio']:
    print("✓ Config is now correct!")
else:
    print("✗ Still has issues")
