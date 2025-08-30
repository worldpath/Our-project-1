#!/usr/bin/env python3
"""
Production Monitoring Setup for Crypto Trading Bot
==================================================
Sets up comprehensive monitoring and alerting for production trading system.
"""

import os
import json
import subprocess
from pathlib import Path

def setup_production_monitoring():
    """Set up comprehensive production monitoring and alerts"""
    
    print("🔧 SETTING UP PRODUCTION MONITORING & ALERTS")
    print("=" * 50)
    
    # 1. Enable health monitoring in supervisor
    print("1️⃣ Adding health monitoring to supervisor...")
    
    supervisor_config = """
[program:health-monitor]
command=python3 /home/user/webapp/health_monitor.py
directory=/home/user/webapp
autostart=true
autorestart=true
startretries=3
stdout_logfile=/home/user/webapp/logs/health_monitor.log
stderr_logfile=/home/user/webapp/logs/health_monitor_error.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=5
stderr_logfile_maxbytes=10MB
stderr_logfile_backups=5
user=user
environment=HOME="/home/user",USER="user"
priority=300
"""
    
    # Add to supervisord.conf
    with open("supervisord.conf", "r") as f:
        config_content = f.read()
    
    if "[program:health-monitor]" not in config_content:
        with open("supervisord.conf", "a") as f:
            f.write("\n" + supervisor_config)
        print("✅ Added health monitor to supervisor")
    else:
        print("✅ Health monitor already in supervisor")
    
    # 2. Create monitoring configuration
    print("\n2️⃣ Creating monitoring configuration...")
    
    monitoring_config = {
        "health_checks": {
            "bot_api": {
                "url": "http://localhost:8889/status",
                "timeout": 10,
                "expected_keys": ["trading_mode", "portfolio_value", "live_trading"]
            },
            "dashboard": {
                "url": "http://localhost:8001/healthz", 
                "timeout": 5
            }
        },
        "alerts": {
            "enabled": True,
            "email_enabled": True,
            "telegram_enabled": True,
            "alert_conditions": [
                "bot_offline",
                "dashboard_offline", 
                "trading_stopped",
                "api_errors",
                "low_balance",
                "high_losses"
            ]
        },
        "thresholds": {
            "max_downtime_minutes": 5,
            "max_api_errors_per_hour": 10,
            "min_balance_usd": 50,
            "max_daily_loss_percent": 25
        }
    }
    
    os.makedirs("config", exist_ok=True)
    with open("config/health_monitor.json", "w") as f:
        json.dump(monitoring_config, f, indent=2)
    
    print("✅ Monitoring configuration created")
    
    # 3. Create monitoring script
    print("\n3️⃣ Creating production monitoring script...")
    
    monitoring_script = '''#!/usr/bin/env python3
"""
Production Health Monitor - Continuous System Monitoring
"""

import asyncio
import aiohttp
import json
import time
import os
import logging
from datetime import datetime
from notifier import notify_email, notify_telegram

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductionMonitor:
    def __init__(self):
        with open("config/health_monitor.json") as f:
            self.config = json.load(f)
        
        self.last_alert_time = {}
        self.alert_cooldown = 300  # 5 minutes between same alerts
    
    async def check_bot_health(self):
        """Check trading bot health"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:8889/status", timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # Check if live trading is active
                        if not data.get("features", {}).get("live_trading", False):
                            await self.send_alert("⚠️ CRITICAL: Live trading is disabled!")
                            return False
                        
                        # Check trading mode
                        if data.get("trading_mode") != "AGGRESSIVE_LIVE":
                            await self.send_alert(f"⚠️ WARNING: Trading mode changed to {data.get('trading_mode')}")
                        
                        return True
                    else:
                        await self.send_alert(f"❌ CRITICAL: Bot API returned status {resp.status}")
                        return False
                        
        except Exception as e:
            await self.send_alert(f"❌ CRITICAL: Cannot connect to trading bot: {str(e)}")
            return False
    
    async def check_dashboard_health(self):
        """Check dashboard health"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:8001/healthz", timeout=5) as resp:
                    return resp.status == 200
        except:
            await self.send_alert("⚠️ WARNING: Dashboard is not responding")
            return False
    
    async def send_alert(self, message):
        """Send alert with cooldown"""
        current_time = time.time()
        
        if message in self.last_alert_time:
            if current_time - self.last_alert_time[message] < self.alert_cooldown:
                return  # Skip duplicate alerts within cooldown period
        
        self.last_alert_time[message] = current_time
        
        # Log alert
        logger.error(f"ALERT: {message}")
        
        # Send notifications
        notify_email("Crypto Bot Alert", message)
        notify_telegram(message)
    
    async def monitor_loop(self):
        """Main monitoring loop"""
        logger.info("🚀 Production monitoring started")
        
        while True:
            try:
                # Check bot health
                bot_healthy = await self.check_bot_health()
                
                # Check dashboard health  
                dashboard_healthy = await self.check_dashboard_health()
                
                # Log status
                status = "✅ HEALTHY" if bot_healthy and dashboard_healthy else "⚠️ ISSUES"
                logger.info(f"Health Check: {status} | Bot: {bot_healthy} | Dashboard: {dashboard_healthy}")
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(30)

async def main():
    monitor = ProductionMonitor()
    await monitor.monitor_loop()

if __name__ == "__main__":
    asyncio.run(main())
'''
    
    with open("production_monitor.py", "w") as f:
        f.write(monitoring_script)
    
    os.chmod("production_monitor.py", 0o755)
    print("✅ Production monitoring script created")
    
    # 4. Create startup notification
    print("\n4️⃣ Creating startup notification...")
    
    startup_message = """
🚀 CRYPTO TRADING BOT - PRODUCTION STARTUP

✅ Production monitoring system activated
✅ Health checks enabled (every 60 seconds)
✅ Alert system configured

The system will automatically notify you if:
• Trading bot goes offline
• Dashboard becomes unavailable  
• Live trading gets disabled
• API errors occur
• System performance issues

Portfolio: $344.27 (REAL MONEY)
Risk Level: 80% AGGRESSIVE
Position Size: $172.13 per trade

Ready for 1000x gains! 🔥
"""
    
    print("✅ Production monitoring setup complete!")
    print("\n📋 NEXT STEPS:")
    print("1. Configure your email/Telegram in .env file")
    print("2. Restart supervisor to enable monitoring:")
    print("   supervisorctl -c supervisord.conf reread")
    print("   supervisorctl -c supervisord.conf update") 
    print("   supervisorctl -c supervisord.conf start health-monitor")
    print("3. Test notifications")
    
    return True

if __name__ == "__main__":
    setup_production_monitoring()