#!/usr/bin/env python3
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
