#!/usr/bin/env python3
"""Test Dashboard Data"""

import requests
import json

# Login and get token
login_data = {"username": "admin", "password": "crypto2024secure"}
response = requests.post("http://localhost:8001/api/login", json=login_data)
token = response.json()['access_token']

# Get dashboard status
headers = {"Authorization": f"Bearer {token}"}
status_response = requests.get("http://localhost:8001/api/status", headers=headers)
data = status_response.json()

bot_status = data['bot_status']
perf = bot_status['performance']
config = bot_status['configuration']

print("🔥 DASHBOARD REAL-TIME DATA:")
print("=" * 40)
print(f"✅ Portfolio Value: {perf['portfolio_value']}")
print(f"✅ Portfolio Risk: {config['portfolio_risk']}")  
print(f"✅ Position Size: {config['max_position_size']}")
print(f"✅ Trading Mode: {bot_status['trading_mode']}")

# Calculate real trading amounts
portfolio = float(perf['portfolio_value'].replace('$', '').replace(',', ''))
pos_pct = float(config['max_position_size'].replace('%', ''))
risk_pct = float(config['portfolio_risk'].replace('%', ''))
per_trade = portfolio * (pos_pct / 100)
max_exp = portfolio * (risk_pct / 100)

print("\n💰 CALCULATED TRADING AMOUNTS:")
print("=" * 40)
print(f"Per Trade Amount: ${per_trade:.2f}")
print(f"Max Portfolio Exposure: ${max_exp:.2f}")
print(f"1000x Gain Potential: ${per_trade * 1000:,.0f}")
print("\n🎉 Dashboard should now show REAL values!")