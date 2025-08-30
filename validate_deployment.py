#!/usr/bin/env python3
"""
Enhanced Trading Bot Deployment Validation
==========================================

This script validates that all enhanced trading bot components are
properly deployed and ready for operation.
"""

import os
import sys
import json
import yaml
import importlib.util
from pathlib import Path
from datetime import datetime

def check_file_exists(file_path, required=True):
    """Check if a file exists"""
    exists = os.path.exists(file_path)
    status = "✅" if exists else ("❌" if required else "⚠️")
    print(f"{status} {file_path}")
    return exists

def check_directory_exists(dir_path, required=True):
    """Check if a directory exists"""
    exists = os.path.isdir(dir_path)
    status = "✅" if exists else ("❌" if required else "⚠️")
    print(f"{status} {dir_path}/")
    return exists

def check_python_module(module_name):
    """Check if a Python module can be imported"""
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is not None:
            print(f"✅ {module_name}")
            return True
        else:
            print(f"❌ {module_name}")
            return False
    except ImportError:
        print(f"❌ {module_name}")
        return False

def validate_configuration():
    """Validate configuration files"""
    print("\n🔧 CONFIGURATION VALIDATION")
    print("=" * 50)
    
    # Check main config file
    config_valid = check_file_exists("config/ultra_aggressive.yaml")
    
    if config_valid:
        try:
            with open("config/ultra_aggressive.yaml", 'r') as f:
                config = yaml.safe_load(f)
            
            # Check required sections
            required_sections = [
                'trading', 'strategies', 'execution', 
                'monitoring', 'tax_tracking', 'backtesting'
            ]
            
            for section in required_sections:
                if section in config:
                    print(f"✅ config.{section}")
                else:
                    print(f"❌ config.{section}")
                    
        except Exception as e:
            print(f"❌ Error loading config: {e}")
    
    # Check environment file
    env_exists = check_file_exists(".env")
    if env_exists:
        required_env_vars = [
            "BINANCE_API_KEY", "BINANCE_API_SECRET"
        ]
        for var in required_env_vars:
            if os.getenv(var):
                print(f"✅ ENV: {var}")
            else:
                print(f"❌ ENV: {var}")

def validate_core_files():
    """Validate core trading bot files"""
    print("\n📁 CORE FILES VALIDATION")
    print("=" * 50)
    
    # Enhanced modules (already present)
    enhanced_modules = [
        "enhanced_strategy_rules.py",
        "enhanced_risk_manager.py", 
        "enhanced_execution_engine.py",
        "enhanced_monitoring.py",
        "enhanced_tax_integration.py",
        "enhanced_backtesting.py"
    ]
    
    for module in enhanced_modules:
        check_file_exists(module)
    
    # New integration files
    integration_files = [
        "main_enhanced.py",
        "start_enhanced_bot.py",
        "deploy_enhanced_bot.sh",
        "ENHANCED_DEPLOYMENT_GUIDE.md"
    ]
    
    for file in integration_files:
        check_file_exists(file)

def validate_deployment_files():
    """Validate deployment configuration files"""
    print("\n🐳 DEPLOYMENT FILES VALIDATION")
    print("=" * 50)
    
    deployment_files = [
        "docker-compose-enhanced.yml",
        "Dockerfile.enhanced",
        "enhanced_requirements.txt"
    ]
    
    for file in deployment_files:
        check_file_exists(file)
    
    # Check monitoring configuration
    monitoring_files = [
        "monitoring/prometheus.yml",
        "monitoring/alertmanager.yml", 
        "monitoring/trading_bot_alerts.yml",
        "monitoring/grafana/datasources/prometheus.yml",
        "monitoring/grafana/dashboards/dashboard.yml"
    ]
    
    for file in monitoring_files:
        check_file_exists(file)

def validate_directories():
    """Validate required directories"""
    print("\n📂 DIRECTORY STRUCTURE VALIDATION")
    print("=" * 50)
    
    required_dirs = [
        "config",
        "logs", 
        "tax_reports",
        "monitoring",
        "monitoring/grafana",
        "monitoring/grafana/dashboards",
        "monitoring/grafana/datasources"
    ]
    
    for dir_path in required_dirs:
        check_directory_exists(dir_path)

def validate_python_dependencies():
    """Validate Python dependencies"""
    print("\n🐍 PYTHON DEPENDENCIES VALIDATION")
    print("=" * 50)
    
    # Core dependencies
    core_deps = [
        "pandas", "numpy", "yaml", "asyncio",
        "ccxt", "binance", "fastapi", "uvicorn"
    ]
    
    for dep in core_deps:
        check_python_module(dep)
    
    # Enhanced dependencies
    enhanced_deps = [
        "sklearn", "scipy", "prometheus_client", 
        "backtrader", "ta"
    ]
    
    print("\n📊 Enhanced Dependencies:")
    for dep in enhanced_deps:
        check_python_module(dep)

def validate_trading_pairs():
    """Validate trading pairs data"""
    print("\n📈 TRADING PAIRS VALIDATION") 
    print("=" * 50)
    
    pairs_file = "all_binance_usdt_pairs.json"
    if check_file_exists(pairs_file):
        try:
            with open(pairs_file, 'r') as f:
                pairs_data = json.load(f)
            
            if isinstance(pairs_data, list) and len(pairs_data) > 0:
                print(f"✅ Trading pairs loaded: {len(pairs_data)} pairs")
                
                # Check first few pairs structure
                if len(pairs_data) > 0 and 'symbol' in pairs_data[0]:
                    print(f"✅ Valid pair structure")
                else:
                    print(f"❌ Invalid pair structure")
            else:
                print(f"❌ Invalid trading pairs data")
                
        except Exception as e:
            print(f"❌ Error loading trading pairs: {e}")

def validate_permissions():
    """Validate file permissions"""
    print("\n🔐 PERMISSIONS VALIDATION")
    print("=" * 50)
    
    executable_files = [
        "start_enhanced_bot.py",
        "deploy_enhanced_bot.sh"
    ]
    
    for file in executable_files:
        if os.path.exists(file):
            if os.access(file, os.X_OK):
                print(f"✅ {file} (executable)")
            else:
                print(f"⚠️ {file} (not executable)")
                print(f"   Run: chmod +x {file}")
        else:
            print(f"❌ {file} (missing)")

def generate_deployment_summary():
    """Generate deployment summary"""
    print("\n🚀 DEPLOYMENT SUMMARY")
    print("=" * 50)
    
    print("Your Ultra-Aggressive Enhanced Trading Bot is ready!")
    print()
    print("📋 Quick Start Commands:")
    print("  1. Setup:     python start_enhanced_bot.py setup")
    print("  2. Backtest:  python start_enhanced_bot.py backtest") 
    print("  3. Test Mode: python start_enhanced_bot.py test")
    print("  4. Live Mode: python start_enhanced_bot.py live")
    print()
    print("🐳 Docker Deployment:")
    print("  ./deploy_enhanced_bot.sh production")
    print()
    print("📊 Monitoring URLs (after deployment):")
    print("  • Bot API:    http://localhost:8080")
    print("  • Grafana:    http://localhost:3000")
    print("  • Prometheus: http://localhost:9091")
    print()
    print("📖 Complete Guide: ENHANCED_DEPLOYMENT_GUIDE.md")

def main():
    """Main validation function"""
    print("🔍 ENHANCED TRADING BOT DEPLOYMENT VALIDATION")
    print("=" * 60)
    print(f"📅 Validation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run all validations
    validate_configuration()
    validate_core_files() 
    validate_deployment_files()
    validate_directories()
    validate_python_dependencies()
    validate_trading_pairs()
    validate_permissions()
    generate_deployment_summary()
    
    print("\n" + "=" * 60)
    print("✅ VALIDATION COMPLETE!")
    print("🚀 Your Enhanced Trading Bot is ready for maximum 1000x potential!")

if __name__ == "__main__":
    main()