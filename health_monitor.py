#!/usr/bin/env python3
"""
Comprehensive Health Monitoring System for Crypto Bot
=====================================================

Features:
- System health monitoring
- Trading performance metrics
- Connection status monitoring
- Resource usage tracking
- Alert system integration
- Web dashboard health endpoints
"""

import os
import psutil
import json
import sqlite3
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests
import asyncio
from dataclasses import dataclass, asdict
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class HealthMetrics:
    """Health metrics data structure"""
    timestamp: datetime
    system_health: Dict[str, Any]
    trading_health: Dict[str, Any]
    connection_health: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    alerts: List[str]
    overall_status: str  # 'healthy', 'warning', 'critical'

class HealthMonitor:
    """Comprehensive health monitoring system"""
    
    def __init__(self, config_path: str = "config/health_monitor.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.db_path = self.config.get('db_path', 'health_monitor.db')
        self._init_database()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load health monitoring configuration"""
        default_config = {
            "monitoring_interval": 60,  # seconds
            "retention_days": 30,
            "alert_thresholds": {
                "cpu_usage": 80.0,
                "memory_usage": 85.0,
                "disk_usage": 90.0,
                "max_trade_age_hours": 2,
                "min_equity": 1000.0,
                "max_daily_loss": 10.0
            },
            "endpoints_to_check": [
                "http://localhost:8000/healthz",
                "http://localhost:8080/healthz"
            ],
            "critical_files": [
                "trade_history.csv",
                "risk_state.json",
                ".env"
            ]
        }
        
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            else:
                # Create default config
                os.makedirs(os.path.dirname(self.config_path) if os.path.dirname(self.config_path) else '.', exist_ok=True)
                with open(self.config_path, 'w') as f:
                    json.dump(default_config, f, indent=2)
                return default_config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return default_config
            
    def _init_database(self):
        """Initialize SQLite database for health metrics"""
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS health_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                cpu_usage REAL,
                memory_usage REAL,
                disk_usage REAL,
                network_connections INTEGER,
                trading_active INTEGER,
                last_trade_time TEXT,
                current_equity REAL,
                daily_pnl REAL,
                open_positions INTEGER,
                endpoint_status TEXT,
                alerts TEXT,
                overall_status TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        connection.commit()
        connection.close()
        
    def get_system_health(self) -> Dict[str, Any]:
        """Get system health metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Network connections
            network_connections = len(psutil.net_connections())
            
            # Process information
            try:
                current_process = psutil.Process()
                process_memory = current_process.memory_info().rss / 1024 / 1024  # MB
                process_cpu = current_process.cpu_percent()
            except:
                process_memory = 0
                process_cpu = 0
                
            return {
                'cpu_usage': round(cpu_percent, 2),
                'memory_usage': round(memory_percent, 2),
                'disk_usage': round(disk_percent, 2),
                'network_connections': network_connections,
                'process_memory_mb': round(process_memory, 2),
                'process_cpu_percent': round(process_cpu, 2),
                'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0],
                'uptime_seconds': time.time() - psutil.boot_time()
            }
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {'error': str(e)}
            
    def get_trading_health(self) -> Dict[str, Any]:
        """Get trading system health metrics"""
        try:
            # Check if trading files exist and are recent
            trade_file = Path('trade_history.csv')
            risk_file = Path('risk_state.json')
            
            trading_health = {
                'trade_file_exists': trade_file.exists(),
                'risk_file_exists': risk_file.exists(),
                'last_trade_time': None,
                'current_equity': 0,
                'daily_pnl': 0,
                'open_positions': 0,
                'trading_active': False
            }
            
            # Check last trade time
            if trade_file.exists():
                try:
                    import pandas as pd
                    df = pd.read_csv(trade_file)
                    if not df.empty and 'timestamp' in df.columns:
                        last_trade = pd.to_datetime(df['timestamp']).max()
                        trading_health['last_trade_time'] = last_trade.isoformat()
                        
                        # Check if trading is active (trade within last 2 hours)
                        hours_since_trade = (datetime.now() - last_trade.to_pydatetime()).total_seconds() / 3600
                        trading_health['trading_active'] = hours_since_trade < 2
                        
                        # Calculate daily PnL
                        today = datetime.now().date()
                        today_trades = df[pd.to_datetime(df['timestamp']).dt.date == today]
                        if 'pnl' in df.columns:
                            trading_health['daily_pnl'] = today_trades['pnl'].sum() if not today_trades.empty else 0
                            
                except Exception as e:
                    logger.error(f"Error reading trade file: {e}")
                    
            # Check risk state
            if risk_file.exists():
                try:
                    with open(risk_file, 'r') as f:
                        risk_data = json.load(f)
                    trading_health['current_equity'] = risk_data.get('current_equity', 0)
                    trading_health['open_positions'] = len(risk_data.get('open_positions', {}))
                except Exception as e:
                    logger.error(f"Error reading risk file: {e}")
                    
            return trading_health
            
        except Exception as e:
            logger.error(f"Error getting trading health: {e}")
            return {'error': str(e)}
            
    def get_connection_health(self) -> Dict[str, Any]:
        """Check connection health for various endpoints"""
        connection_health = {
            'endpoints': {},
            'all_healthy': True
        }
        
        for endpoint in self.config.get('endpoints_to_check', []):
            try:
                response = requests.get(endpoint, timeout=5)
                status = {
                    'status_code': response.status_code,
                    'response_time_ms': round(response.elapsed.total_seconds() * 1000, 2),
                    'healthy': response.status_code == 200
                }
                
                if not status['healthy']:
                    connection_health['all_healthy'] = False
                    
            except Exception as e:
                status = {
                    'error': str(e),
                    'healthy': False
                }
                connection_health['all_healthy'] = False
                
            connection_health['endpoints'][endpoint] = status
            
        return connection_health
        
    def check_critical_files(self) -> Dict[str, Any]:
        """Check if critical files exist and are recent"""
        file_health = {'all_files_ok': True, 'files': {}}
        
        for file_path in self.config.get('critical_files', []):
            path = Path(file_path)
            file_info = {
                'exists': path.exists(),
                'size_bytes': path.stat().st_size if path.exists() else 0,
                'modified_time': datetime.fromtimestamp(path.stat().st_mtime).isoformat() if path.exists() else None,
                'age_hours': 0
            }
            
            if path.exists():
                age_seconds = time.time() - path.stat().st_mtime
                file_info['age_hours'] = round(age_seconds / 3600, 2)
            else:
                file_health['all_files_ok'] = False
                
            file_health['files'][file_path] = file_info
            
        return file_health
        
    def generate_alerts(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate alerts based on health metrics"""
        alerts = []
        thresholds = self.config.get('alert_thresholds', {})
        
        # System alerts
        if 'system_health' in metrics:
            system = metrics['system_health']
            if system.get('cpu_usage', 0) > thresholds.get('cpu_usage', 80):
                alerts.append(f"High CPU usage: {system['cpu_usage']}%")
            if system.get('memory_usage', 0) > thresholds.get('memory_usage', 85):
                alerts.append(f"High memory usage: {system['memory_usage']}%")
            if system.get('disk_usage', 0) > thresholds.get('disk_usage', 90):
                alerts.append(f"High disk usage: {system['disk_usage']}%")
                
        # Trading alerts
        if 'trading_health' in metrics:
            trading = metrics['trading_health']
            if not trading.get('trading_active', False):
                alerts.append("Trading appears inactive - no recent trades")
            if trading.get('current_equity', 0) < thresholds.get('min_equity', 1000):
                alerts.append(f"Low equity: ${trading['current_equity']}")
            if trading.get('daily_pnl', 0) < -thresholds.get('max_daily_loss', 10):
                alerts.append(f"High daily loss: ${trading['daily_pnl']}")
                
        # Connection alerts
        if 'connection_health' in metrics:
            conn = metrics['connection_health']
            if not conn.get('all_healthy', True):
                alerts.append("Some endpoint health checks failed")
                
        return alerts
        
    def collect_health_metrics(self) -> HealthMetrics:
        """Collect comprehensive health metrics"""
        timestamp = datetime.now(timezone.utc)
        
        # Collect all metrics
        system_health = self.get_system_health()
        trading_health = self.get_trading_health()
        connection_health = self.get_connection_health()
        file_health = self.check_critical_files()
        
        # Performance metrics (simplified)
        performance_metrics = {
            'file_health': file_health,
            'last_collection_time': timestamp.isoformat()
        }
        
        # Combine all metrics for alert generation
        all_metrics = {
            'system_health': system_health,
            'trading_health': trading_health,
            'connection_health': connection_health,
            'performance_metrics': performance_metrics
        }
        
        # Generate alerts
        alerts = self.generate_alerts(all_metrics)
        
        # Determine overall status
        if alerts:
            if any('critical' in alert.lower() or 'high' in alert.lower() for alert in alerts):
                overall_status = 'critical'
            else:
                overall_status = 'warning'
        else:
            overall_status = 'healthy'
            
        return HealthMetrics(
            timestamp=timestamp,
            system_health=system_health,
            trading_health=trading_health,
            connection_health=connection_health,
            performance_metrics=performance_metrics,
            alerts=alerts,
            overall_status=overall_status
        )
        
    def save_health_metrics(self, metrics: HealthMetrics):
        """Save health metrics to database"""
        try:
            connection = sqlite3.connect(self.db_path)
            cursor = connection.cursor()
            
            cursor.execute('''
                INSERT INTO health_metrics 
                (timestamp, cpu_usage, memory_usage, disk_usage, network_connections,
                 trading_active, last_trade_time, current_equity, daily_pnl, open_positions,
                 endpoint_status, alerts, overall_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metrics.timestamp.isoformat(),
                metrics.system_health.get('cpu_usage'),
                metrics.system_health.get('memory_usage'),
                metrics.system_health.get('disk_usage'),
                metrics.system_health.get('network_connections'),
                1 if metrics.trading_health.get('trading_active') else 0,
                metrics.trading_health.get('last_trade_time'),
                metrics.trading_health.get('current_equity'),
                metrics.trading_health.get('daily_pnl'),
                metrics.trading_health.get('open_positions'),
                json.dumps(metrics.connection_health),
                json.dumps(metrics.alerts),
                metrics.overall_status
            ))
            
            connection.commit()
            connection.close()
            
        except Exception as e:
            logger.error(f"Error saving health metrics: {e}")
            
    def get_health_summary(self) -> Dict[str, Any]:
        """Get current health summary"""
        metrics = self.collect_health_metrics()
        return asdict(metrics)
        
    def run_health_check(self) -> Dict[str, Any]:
        """Run complete health check and return results"""
        metrics = self.collect_health_metrics()
        self.save_health_metrics(metrics)
        
        # Send alerts if configured
        if metrics.alerts and self.config.get('send_alerts', False):
            self._send_health_alerts(metrics.alerts)
            
        return asdict(metrics)
        
    def _send_health_alerts(self, alerts: List[str]):
        """Send health alerts via configured channels"""
        try:
            from notifier import notify_email, notify_telegram
            
            alert_message = "🚨 Health Monitor Alerts:\n" + "\n".join(f"• {alert}" for alert in alerts)
            
            notify_email("Health Monitor Alert", alert_message)
            notify_telegram(alert_message)
            
        except Exception as e:
            logger.error(f"Error sending health alerts: {e}")
            
    def cleanup_old_data(self, days: int = None):
        """Clean up old health monitoring data"""
        if days is None:
            days = self.config.get('retention_days', 30)
            
        try:
            connection = sqlite3.connect(self.db_path)
            cursor = connection.cursor()
            
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            cursor.execute('DELETE FROM health_metrics WHERE timestamp < ?', (cutoff_date,))
            
            deleted_rows = cursor.rowcount
            connection.commit()
            connection.close()
            
            logger.info(f"Cleaned up {deleted_rows} old health records")
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")

# Health check endpoint for web integration
def health_check_endpoint() -> Dict[str, Any]:
    """Simple health check endpoint for web services"""
    monitor = HealthMonitor()
    return monitor.get_health_summary()

if __name__ == "__main__":
    # Example usage
    monitor = HealthMonitor()
    
    # Run health check
    health_status = monitor.run_health_check()
    print(json.dumps(health_status, indent=2, default=str))
    
    # Clean up old data
    monitor.cleanup_old_data()