#!/usr/bin/env python3
"""
Comprehensive Startup System for Crypto Bot
===========================================

Features:
- System initialization and health checks
- Service dependency management
- Environment validation
- Database initialization
- Configuration validation
- Automated startup sequence
- Error recovery and failsafe mechanisms
"""

import os
import sys
import json
import time
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import psutil
import sqlite3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StartupSystem:
    """Comprehensive startup system for crypto bot"""
    
    def __init__(self, config_path: str = "config/aggressive_production.yaml"):
        self.config_path = config_path
        self.startup_log = []
        self.startup_time = datetime.now(timezone.utc)
        
    def log_startup_event(self, event: str, status: str, details: str = ""):
        """Log startup events"""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "status": status,
            "details": details
        }
        self.startup_log.append(entry)
        
        if status == "success":
            logger.info(f"✅ {event}: {details}")
        elif status == "warning":
            logger.warning(f"⚠️ {event}: {details}")
        elif status == "error":
            logger.error(f"❌ {event}: {details}")
        else:
            logger.info(f"ℹ️ {event}: {details}")
            
    def check_system_requirements(self) -> bool:
        """Check system requirements and dependencies"""
        self.log_startup_event("System Requirements Check", "info", "Starting system validation")
        
        # Check Python version
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        if sys.version_info >= (3, 8):
            self.log_startup_event("Python Version", "success", f"Python {python_version} - OK")
        else:
            self.log_startup_event("Python Version", "error", f"Python {python_version} - Requires 3.8+")
            return False
            
        # Check available memory
        memory = psutil.virtual_memory()
        memory_gb = memory.total / (1024**3)
        if memory_gb >= 1.0:
            self.log_startup_event("Memory Check", "success", f"{memory_gb:.1f}GB available")
        else:
            self.log_startup_event("Memory Check", "warning", f"{memory_gb:.1f}GB available - Low memory")
            
        # Check disk space
        disk = psutil.disk_usage('.')
        disk_gb = disk.free / (1024**3)
        if disk_gb >= 5.0:
            self.log_startup_event("Disk Space", "success", f"{disk_gb:.1f}GB free")
        else:
            self.log_startup_event("Disk Space", "warning", f"{disk_gb:.1f}GB free - Low disk space")
            
        # Check required directories
        required_dirs = ['config', 'backups']
        for dir_name in required_dirs:
            dir_path = Path(dir_name)
            if dir_path.exists():
                self.log_startup_event("Directory Check", "success", f"{dir_name}/ exists")
            else:
                dir_path.mkdir(exist_ok=True)
                self.log_startup_event("Directory Check", "warning", f"Created missing directory: {dir_name}/")
                
        return True
        
    def validate_environment(self) -> bool:
        """Validate environment configuration"""
        self.log_startup_event("Environment Validation", "info", "Checking environment variables")
        
        # Required environment variables
        required_vars = [
            'BINANCE_API_KEY',
            'BINANCE_API_SECRET',
        ]
        
        optional_vars = [
            'DASHBOARD_USER',
            'DASHBOARD_PASS',
            'DASHBOARD_JWT_SECRET'
        ]
        
        missing_required = []
        missing_optional = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_required.append(var)
                
        for var in optional_vars:
            if not os.getenv(var):
                missing_optional.append(var)
                
        if missing_required:
            self.log_startup_event("Environment Variables", "error", f"Missing required: {', '.join(missing_required)}")
            return False
            
        if missing_optional:
            self.log_startup_event("Environment Variables", "warning", f"Missing optional: {', '.join(missing_optional)}")
        else:
            self.log_startup_event("Environment Variables", "success", "All environment variables present")
            
        return True
        
    def validate_configuration(self) -> bool:
        """Validate configuration files"""
        self.log_startup_event("Configuration Validation", "info", "Checking configuration files")
        
        # Check main config file
        if not Path(self.config_path).exists():
            self.log_startup_event("Configuration File", "error", f"Config file not found: {self.config_path}")
            return False
        else:
            self.log_startup_event("Configuration File", "success", f"Config file exists: {self.config_path}")
            
        # Validate .env file
        env_file = Path('.env')
        if not env_file.exists():
            self.log_startup_event("Environment File", "warning", ".env file not found - using .env.example as template")
            # Copy .env.example to .env
            example_file = Path('.env.example')
            if example_file.exists():
                import shutil
                shutil.copy(example_file, env_file)
                self.log_startup_event("Environment File", "success", "Created .env from .env.example")
            else:
                self.log_startup_event("Environment File", "error", "No .env.example found")
                return False
        else:
            self.log_startup_event("Environment File", "success", ".env file exists")
            
        return True
        
    def initialize_databases(self) -> bool:
        """Initialize required databases"""
        self.log_startup_event("Database Initialization", "info", "Setting up databases")
        
        try:
            # Initialize tax tracking database
            from tax_tracker import TaxTracker
            tax_tracker = TaxTracker()
            tax_tracker.close()
            self.log_startup_event("Tax Database", "success", "Tax tracking database initialized")
            
        except Exception as e:
            self.log_startup_event("Tax Database", "error", f"Tax database initialization failed: {e}")
            return False
            
        try:
            # Initialize health monitoring database
            from health_monitor import HealthMonitor
            health_monitor = HealthMonitor()
            self.log_startup_event("Health Database", "success", "Health monitoring database initialized")
            
        except Exception as e:
            self.log_startup_event("Health Database", "error", f"Health monitoring initialization failed: {e}")
            return False
            
        return True
        
    def check_network_connectivity(self) -> bool:
        """Check network connectivity to external services"""
        self.log_startup_event("Network Connectivity", "info", "Testing network connections")
        
        # Test endpoints
        test_endpoints = [
            ("Binance API", "https://api.binance.com/api/v3/time"),
            ("Binance US API", "https://api.binance.us/api/v3/time"),
        ]
        
        import requests
        
        all_connected = True
        
        for name, url in test_endpoints:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    self.log_startup_event("Network Test", "success", f"{name} - OK")
                else:
                    self.log_startup_event("Network Test", "warning", f"{name} - HTTP {response.status_code}")
                    all_connected = False
            except Exception as e:
                self.log_startup_event("Network Test", "error", f"{name} - {str(e)}")
                all_connected = False
                
        return all_connected
        
    def check_required_packages(self) -> bool:
        """Check if required Python packages are installed"""
        self.log_startup_event("Package Dependencies", "info", "Checking Python packages")
        
        required_packages = [
            'pandas', 'numpy', 'fastapi', 'uvicorn', 'ccxt', 
            'python-binance', 'ta', 'pyyaml', 'psutil'
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                self.log_startup_event("Package Check", "success", f"{package} - Available")
            except ImportError:
                missing_packages.append(package)
                self.log_startup_event("Package Check", "error", f"{package} - Missing")
                
        if missing_packages:
            self.log_startup_event("Package Dependencies", "error", f"Missing packages: {', '.join(missing_packages)}")
            return False
        else:
            self.log_startup_event("Package Dependencies", "success", "All required packages available")
            return True
            
    def create_initial_files(self):
        """Create initial files if they don't exist"""
        self.log_startup_event("Initial Files", "info", "Creating initial files")
        
        # Create trade history file with headers
        trade_file = Path('trade_history.csv')
        if not trade_file.exists():
            with open(trade_file, 'w') as f:
                f.write('timestamp_utc,symbol,side,qty,price,order_id,tag,note,pnl_quote,fees\n')
            self.log_startup_event("Trade History", "success", "Created trade_history.csv")
            
        # Create risk state file
        risk_file = Path('risk_state.json')
        if not risk_file.exists():
            initial_risk_state = {
                "current_equity": 10000.0,
                "open_positions": {},
                "daily_pnl": 0.0,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            with open(risk_file, 'w') as f:
                json.dump(initial_risk_state, f, indent=2)
            self.log_startup_event("Risk State", "success", "Created risk_state.json")
            
    def perform_startup_sequence(self) -> Dict[str, Any]:
        """Perform complete startup sequence"""
        logger.info("🚀 Starting Crypto Bot Startup Sequence")
        logger.info(f"Startup Time: {self.startup_time.isoformat()}")
        logger.info("=" * 60)
        
        startup_steps = [
            ("System Requirements", self.check_system_requirements),
            ("Environment Variables", self.validate_environment),
            ("Configuration Files", self.validate_configuration),
            ("Python Packages", self.check_required_packages),
            ("Database Setup", self.initialize_databases),
            ("Network Connectivity", self.check_network_connectivity),
            ("Initial Files", lambda: (self.create_initial_files(), True)[1])
        ]
        
        overall_success = True
        
        for step_name, step_function in startup_steps:
            logger.info(f"\n📋 Executing: {step_name}")
            try:
                success = step_function()
                if not success:
                    overall_success = False
                    logger.error(f"❌ {step_name} failed - continuing with remaining steps")
            except Exception as e:
                overall_success = False
                self.log_startup_event(step_name, "error", f"Exception: {str(e)}")
                logger.exception(f"❌ {step_name} failed with exception")
                
        # Generate startup report
        startup_report = {
            "startup_time": self.startup_time.isoformat(),
            "completion_time": datetime.now(timezone.utc).isoformat(),
            "overall_success": overall_success,
            "startup_log": self.startup_log,
            "system_info": {
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "platform": sys.platform,
                "cpu_count": psutil.cpu_count(),
                "memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "disk_free_gb": round(psutil.disk_usage('.').free / (1024**3), 2)
            }
        }
        
        # Save startup report
        report_file = f"startup_report_{self.startup_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(startup_report, f, indent=2, default=str)
            
        logger.info("\n" + "=" * 60)
        if overall_success:
            logger.info("✅ Startup sequence completed successfully!")
            logger.info("🤖 Crypto Bot is ready for operation")
        else:
            logger.error("❌ Startup sequence completed with errors")
            logger.error("⚠️  Please review the startup log and fix issues before starting trading")
            
        logger.info(f"📄 Startup report saved to: {report_file}")
        
        return startup_report
        
    def run_health_check(self) -> bool:
        """Run post-startup health check"""
        try:
            from health_monitor import HealthMonitor
            health_monitor = HealthMonitor()
            health_status = health_monitor.run_health_check()
            
            overall_status = health_status.get('overall_status', 'unknown')
            
            if overall_status == 'healthy':
                self.log_startup_event("Post-Startup Health Check", "success", "System is healthy")
                return True
            else:
                self.log_startup_event("Post-Startup Health Check", "warning", f"System status: {overall_status}")
                return False
                
        except Exception as e:
            self.log_startup_event("Post-Startup Health Check", "error", f"Health check failed: {e}")
            return False

def main():
    """Main startup function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Crypto Bot Startup System")
    parser.add_argument("--config", default="config/aggressive_production.yaml", 
                       help="Configuration file path")
    parser.add_argument("--health-check", action="store_true", 
                       help="Run health check after startup")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    # Run startup sequence
    startup_system = StartupSystem(config_path=args.config)
    report = startup_system.perform_startup_sequence()
    
    # Run health check if requested
    if args.health_check:
        health_ok = startup_system.run_health_check()
        report['post_startup_health_check'] = health_ok
        
    # Exit with appropriate code
    if report['overall_success']:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()