#!/usr/bin/env python3
"""
Deployment Health Check Script for Crypto Bot
=============================================

This script performs comprehensive health checks on the deployed crypto bot
and provides detailed status reports for monitoring and troubleshooting.
"""

import requests
import json
import sys
import argparse
from datetime import datetime
from pathlib import Path
import subprocess
import time

class DeploymentHealthChecker:
    """Comprehensive deployment health checker"""
    
    def __init__(self, server_ip: str = "207.246.99.108", use_ssh: bool = False):
        self.server_ip = server_ip
        self.use_ssh = use_ssh
        self.base_url = f"http://{server_ip}"
        self.base_https_url = f"https://{server_ip}"
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "server_ip": server_ip,
            "checks": {},
            "overall_status": "unknown",
            "alerts": []
        }
        
    def check_network_connectivity(self):
        """Check basic network connectivity to server"""
        print(f"🔌 Checking network connectivity to {self.server_ip}...")
        
        try:
            # Ping test
            result = subprocess.run(
                ["ping", "-c", "3", self.server_ip], 
                capture_output=True, 
                text=True, 
                timeout=15
            )
            
            ping_success = result.returncode == 0
            
            self.results["checks"]["network_connectivity"] = {
                "status": "pass" if ping_success else "fail",
                "ping_result": result.stdout if ping_success else result.stderr,
                "response_time": "Available in ping output" if ping_success else "N/A"
            }
            
            if ping_success:
                print(f"✅ Network connectivity: OK")
            else:
                print(f"❌ Network connectivity: FAILED")
                self.results["alerts"].append(f"Network connectivity to {self.server_ip} failed")
                
        except subprocess.TimeoutExpired:
            print(f"❌ Network connectivity: TIMEOUT")
            self.results["checks"]["network_connectivity"] = {
                "status": "fail",
                "error": "Ping timeout after 15 seconds"
            }
            self.results["alerts"].append("Network ping timeout")
            
        except Exception as e:
            print(f"❌ Network connectivity: ERROR - {e}")
            self.results["checks"]["network_connectivity"] = {
                "status": "error",
                "error": str(e)
            }
            
    def check_http_services(self):
        """Check HTTP services on various ports"""
        print(f"🌐 Checking HTTP services...")
        
        ports_to_check = [
            (80, "HTTP Web Server"),
            (443, "HTTPS Web Server"), 
            (8000, "Dashboard Service"),
            (8080, "Alternative Dashboard"),
            (3000, "Development Server"),
            (5000, "Flask Service")
        ]
        
        http_results = {}
        
        for port, description in ports_to_check:
            print(f"  Checking {description} on port {port}...")
            
            try:
                # Try both HTTP and HTTPS
                urls_to_try = []
                if port in [80, 8000, 8080, 3000, 5000]:
                    urls_to_try.append(f"http://{self.server_ip}:{port}")
                if port in [443]:
                    urls_to_try.append(f"https://{self.server_ip}")
                if port == 80:
                    urls_to_try.append(f"http://{self.server_ip}")
                    
                success = False
                response_data = {}
                
                for url in urls_to_try:
                    try:
                        response = requests.get(f"{url}/healthz", timeout=10)
                        if response.status_code == 200:
                            success = True
                            response_data = {
                                "url": url,
                                "status_code": response.status_code,
                                "response_time_ms": round(response.elapsed.total_seconds() * 1000, 2),
                                "content_length": len(response.content),
                                "headers": dict(response.headers)
                            }
                            print(f"    ✅ {description}: OK ({url})")
                            break
                    except requests.exceptions.RequestException:
                        # Try root endpoint
                        try:
                            response = requests.get(url, timeout=10)
                            if response.status_code in [200, 404, 401, 403]:  # Any response means service is running
                                success = True
                                response_data = {
                                    "url": url,
                                    "status_code": response.status_code,
                                    "response_time_ms": round(response.elapsed.total_seconds() * 1000, 2),
                                    "note": "Service responding but /healthz endpoint not available"
                                }
                                print(f"    ⚠️  {description}: Service running but no health endpoint ({url})")
                                break
                        except:
                            continue
                            
                if not success:
                    print(f"    ❌ {description}: Not accessible")
                    response_data = {"status": "unreachable", "ports_tried": [port]}
                    
                http_results[f"port_{port}"] = response_data
                
            except Exception as e:
                print(f"    ❌ {description}: ERROR - {e}")
                http_results[f"port_{port}"] = {"status": "error", "error": str(e)}
                
        self.results["checks"]["http_services"] = http_results
        
    def check_bot_health_endpoints(self):
        """Check specific crypto bot health endpoints"""
        print(f"🤖 Checking crypto bot health endpoints...")
        
        endpoints_to_check = [
            "/healthz",
            "/api/status",
            "/api/health", 
            "/api/positions",
            "/api/metrics"
        ]
        
        # Try common ports where dashboard might be running
        base_urls = [
            f"http://{self.server_ip}",
            f"http://{self.server_ip}:8000",
            f"http://{self.server_ip}:8080",
            f"https://{self.server_ip}"
        ]
        
        bot_health = {}
        
        for base_url in base_urls:
            print(f"  Trying base URL: {base_url}")
            
            url_results = {}
            working_base = False
            
            for endpoint in endpoints_to_check:
                try:
                    full_url = f"{base_url}{endpoint}"
                    response = requests.get(full_url, timeout=10)
                    
                    url_results[endpoint] = {
                        "status_code": response.status_code,
                        "response_time_ms": round(response.elapsed.total_seconds() * 1000, 2),
                        "accessible": response.status_code in [200, 401, 403]  # 401/403 means auth required but service works
                    }
                    
                    if response.status_code == 200:
                        working_base = True
                        try:
                            url_results[endpoint]["data"] = response.json()
                        except:
                            url_results[endpoint]["data"] = "Non-JSON response"
                        print(f"    ✅ {endpoint}: OK")
                    elif response.status_code in [401, 403]:
                        working_base = True
                        print(f"    🔐 {endpoint}: Authentication required")
                    else:
                        print(f"    ⚠️  {endpoint}: Status {response.status_code}")
                        
                except requests.exceptions.RequestException as e:
                    url_results[endpoint] = {"error": str(e), "accessible": False}
                    print(f"    ❌ {endpoint}: {e}")
                    
            if working_base:
                bot_health[base_url] = url_results
                print(f"    ✅ Found working bot service at {base_url}")
                break
            else:
                bot_health[base_url] = {"status": "no_working_endpoints", "endpoints": url_results}
                
        self.results["checks"]["bot_health"] = bot_health
        
    def check_system_services(self):
        """Check system services if SSH access is available"""
        print(f"🔧 Checking system services...")
        
        if not self.use_ssh:
            print("  ℹ️  SSH access not configured - skipping system service checks")
            self.results["checks"]["system_services"] = {"status": "skipped", "reason": "No SSH access"}
            return
            
        # Services to check
        services_to_check = [
            "crypto-bot",
            "crypto-bot-dashboard", 
            "nginx",
            "caddy"
        ]
        
        service_status = {}
        
        for service in services_to_check:
            try:
                # Check service status via SSH
                ssh_command = f"ssh -o ConnectTimeout=10 ubuntu@{self.server_ip} 'systemctl is-active {service}'"
                result = subprocess.run(ssh_command.split(), capture_output=True, text=True, timeout=15)
                
                is_active = result.stdout.strip() == "active"
                service_status[service] = {
                    "active": is_active,
                    "status_output": result.stdout.strip(),
                    "error_output": result.stderr.strip() if result.stderr else None
                }
                
                if is_active:
                    print(f"    ✅ {service}: Active")
                else:
                    print(f"    ❌ {service}: {result.stdout.strip()}")
                    
            except Exception as e:
                service_status[service] = {"error": str(e)}
                print(f"    ❌ {service}: Error checking - {e}")
                
        self.results["checks"]["system_services"] = service_status
        
    def check_ssl_certificates(self):
        """Check SSL certificate status"""
        print(f"🔒 Checking SSL certificates...")
        
        try:
            # Check HTTPS endpoint
            response = requests.get(f"https://{self.server_ip}", timeout=10, verify=True)
            
            self.results["checks"]["ssl_certificates"] = {
                "https_accessible": True,
                "certificate_valid": True,
                "status_code": response.status_code
            }
            print(f"    ✅ SSL certificate: Valid and accessible")
            
        except requests.exceptions.SSLError as e:
            self.results["checks"]["ssl_certificates"] = {
                "https_accessible": False,
                "certificate_valid": False,
                "ssl_error": str(e)
            }
            print(f"    ❌ SSL certificate: Invalid - {e}")
            self.results["alerts"].append("SSL certificate issues detected")
            
        except requests.exceptions.RequestException as e:
            self.results["checks"]["ssl_certificates"] = {
                "https_accessible": False,
                "connection_error": str(e)
            }
            print(f"    ⚠️  HTTPS not accessible: {e}")
            
    def determine_overall_status(self):
        """Determine overall deployment health status"""
        
        critical_failures = len([alert for alert in self.results["alerts"] if "fail" in alert.lower()])
        
        # Check if any bot health endpoints are working
        bot_working = False
        if "bot_health" in self.results["checks"]:
            for base_url, endpoints in self.results["checks"]["bot_health"].items():
                if isinstance(endpoints, dict) and any(
                    endpoint_data.get("accessible", False) 
                    for endpoint_data in endpoints.values() 
                    if isinstance(endpoint_data, dict)
                ):
                    bot_working = True
                    break
                    
        # Check if network is working
        network_working = (
            self.results["checks"].get("network_connectivity", {}).get("status") == "pass"
        )
        
        if not network_working:
            self.results["overall_status"] = "critical"
        elif not bot_working:
            self.results["overall_status"] = "degraded"  
        elif len(self.results["alerts"]) > 0:
            self.results["overall_status"] = "warning"
        else:
            self.results["overall_status"] = "healthy"
            
    def run_all_checks(self):
        """Run all health checks"""
        print(f"\n🔍 Starting deployment health check for {self.server_ip}")
        print(f"Timestamp: {self.results['timestamp']}")
        print("=" * 60)
        
        self.check_network_connectivity()
        print()
        self.check_http_services() 
        print()
        self.check_bot_health_endpoints()
        print()
        self.check_system_services()
        print()
        self.check_ssl_certificates()
        print()
        
        self.determine_overall_status()
        
        return self.results
        
    def print_summary(self):
        """Print summary of health check results"""
        print("=" * 60)
        print("📊 HEALTH CHECK SUMMARY")
        print("=" * 60)
        
        status_emoji = {
            "healthy": "✅",
            "warning": "⚠️", 
            "degraded": "🟡",
            "critical": "❌",
            "unknown": "❓"
        }
        
        print(f"Overall Status: {status_emoji.get(self.results['overall_status'], '❓')} {self.results['overall_status'].upper()}")
        print(f"Server IP: {self.results['server_ip']}")
        print(f"Check Time: {self.results['timestamp']}")
        print()
        
        if self.results["alerts"]:
            print("🚨 ALERTS:")
            for alert in self.results["alerts"]:
                print(f"  • {alert}")
            print()
            
        print("📋 CHECK RESULTS:")
        for check_name, check_data in self.results["checks"].items():
            if isinstance(check_data, dict) and "status" in check_data:
                status_symbol = "✅" if check_data["status"] == "pass" else "❌" if check_data["status"] == "fail" else "⚠️"
                print(f"  {status_symbol} {check_name.replace('_', ' ').title()}: {check_data['status']}")
            else:
                print(f"  📝 {check_name.replace('_', ' ').title()}: Data available")
                
    def export_results(self, filename: str = None):
        """Export results to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"health_check_{self.server_ip}_{timestamp}.json"
            
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
            
        print(f"📄 Results exported to: {filename}")
        return filename

def main():
    parser = argparse.ArgumentParser(description="Crypto Bot Deployment Health Checker")
    parser.add_argument("--server", default="207.246.99.108", help="Server IP address")
    parser.add_argument("--ssh", action="store_true", help="Enable SSH checks (requires SSH key setup)")
    parser.add_argument("--export", help="Export results to specific filename")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    
    args = parser.parse_args()
    
    # Run health check
    checker = DeploymentHealthChecker(server_ip=args.server, use_ssh=args.ssh)
    results = checker.run_all_checks()
    
    if not args.quiet:
        checker.print_summary()
        
    # Export results
    export_filename = checker.export_results(args.export)
    
    # Exit with appropriate code
    if results["overall_status"] == "critical":
        sys.exit(2)
    elif results["overall_status"] in ["warning", "degraded"]:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()