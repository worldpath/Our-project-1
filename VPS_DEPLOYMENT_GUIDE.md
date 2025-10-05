
# VPS Deployment Guide

Complete guide for deploying the crypto trading bot on a VPS (Virtual Private Server).

## Prerequisites

- VPS with Ubuntu 20.04+ (recommended: 2GB RAM, 2 CPU cores)
- SSH access to your VPS
- Domain name (optional, for dashboard)
- Binance.US API credentials

## Step 1: Prepare VPS

### 1.1 Update System

```bash
ssh user@your_vps_ip

sudo apt update && sudo apt upgrade -y
```

### 1.2 Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### 1.3 Configure Firewall

```bash
# Install UFW if not already installed
sudo apt install ufw -y

# Allow SSH
sudo ufw allow 22/tcp

# Allow API port (8889) - ONLY if you need external access
# Be cautious about exposing this port
sudo ufw allow 8889/tcp

# Enable firewall
sudo ufw enable
sudo ufw status
```

## Step 2: Deploy Bot

### 2.1 Clone Repository

```bash
cd ~
git clone https://github.com/worldpath/Our-project-1.git
cd Our-project-1
```

### 2.2 Configure Environment

```bash
# Create .env from example
cp .env.example .env

# Edit with your credentials
nano .env
```

Update these critical values:

```env
BINANCE_API_KEY=your_actual_api_key
BINANCE_API_SECRET=your_actual_api_secret
TRADING_MODE=live
API_KEY=your_generated_secure_key
```

**Generate a secure API key:**

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 2.3 Test Configuration

```bash
# Test Binance connection
python3 test_binance_connection.py

# Should output: "✓ Binance.US connection successful"
```

### 2.4 Start Bot

```bash
# Start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f crypto_bot

# You should see:
# - "Bot initialized successfully"
# - "API server running on http://0.0.0.0:8889"
# - "Connected to Binance.US"
```

### 2.5 Verify Bot Health

```bash
# Check container status
docker-compose ps

# Test API (replace YOUR_API_KEY)
curl -H "X-API-Key: YOUR_API_KEY" http://localhost:8889/health

# Should return: {"status": "healthy", ...}
```

## Step 3: Configure Dashboard Connection

### 3.1 Get VPS IP Address

```bash
curl ifconfig.me
# Note this IP address
```

### 3.2 Test API from Dashboard Server

From your dashboard deployment environment:

```bash
# Replace with your VPS IP and API key
curl -H "X-API-Key: YOUR_API_KEY" http://YOUR_VPS_IP:8889/health
```

If this fails:
- Check VPS firewall rules
- Verify bot is running: `docker-compose ps`
- Check bot logs: `docker-compose logs crypto_bot`

### 3.3 Update Dashboard Environment

In your dashboard's `.env` file:

```env
VPS_API_URL=http://YOUR_VPS_IP:8889
VPS_API_KEY=your_bot_api_key
VPS_BOT_URL=http://YOUR_VPS_IP:8889
```

## Step 4: Secure Your Deployment

### 4.1 Restrict API Access

**Option A: IP Whitelist (Recommended)**

```bash
# Only allow dashboard server IP
sudo ufw delete allow 8889/tcp
sudo ufw allow from DASHBOARD_IP to any port 8889

# Verify
sudo ufw status
```

**Option B: VPN (Most Secure)**

Set up a VPN between your VPS and dashboard server, then bind API to VPN interface only.

### 4.2 Restrict Binance API Permissions

In your Binance.US account:
1. Go to API Management
2. Edit your API key
3. **Disable withdrawals** ✓ (Critical!)
4. Enable only: "Enable Reading", "Enable Spot Trading"
5. Set IP whitelist to your VPS IP

### 4.3 Enable Auto-Start on Reboot

```bash
# Create systemd service
sudo nano /etc/systemd/system/crypto-bot.service
```

Add:

```ini
[Unit]
Description=Crypto Trading Bot
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/YOUR_USER/Our-project-1
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
User=YOUR_USER

[Install]
WantedBy=multi-user.target
```

Enable:

```bash
sudo systemctl enable crypto-bot
sudo systemctl start crypto-bot
```

## Step 5: Monitoring & Maintenance

### 5.1 Monitor Bot

```bash
# View real-time logs
docker-compose logs -f crypto_bot

# Check positions
curl -H "X-API-Key: YOUR_KEY" http://localhost:8889/positions

# Check balance
curl -H "X-API-Key: YOUR_KEY" http://localhost:8889/balance
```

### 5.2 Regular Maintenance

**Daily:**
- Check dashboard for any alerts
- Review trading performance
- Verify bot is running: `docker-compose ps`

**Weekly:**
- Review logs for errors: `docker-compose logs --tail=100`
- Update bot if new version available
- Rotate API keys

**Monthly:**
- Update VPS packages: `sudo apt update && sudo apt upgrade`
- Review and adjust risk parameters
- Backup configuration

### 5.3 Set Up Log Rotation

```bash
sudo nano /etc/logrotate.d/docker-crypto-bot
```

Add:

```
/var/lib/docker/containers/*/*.log {
  rotate 7
  daily
  compress
  missingok
  delaycompress
  copytruncate
}
```

## Step 6: Troubleshooting

### Bot Not Starting

```bash
# Check logs
docker-compose logs crypto_bot

# Common issues:
# 1. Invalid API credentials
# 2. Port 8889 already in use
# 3. Insufficient permissions

# Rebuild container
docker-compose down
docker-compose up -d --build
```

### API Not Accessible from Dashboard

```bash
# On VPS, check if API is running
netstat -tlnp | grep 8889

# Check firewall
sudo ufw status

# Test locally
curl http://localhost:8889/health

# Test from dashboard server
curl http://VPS_IP:8889/health
```

### Out of Memory Errors

```bash
# Check memory usage
free -h
docker stats

# If needed, add swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## Step 7: Updating Bot

### 7.1 Pull Latest Changes

```bash
cd ~/Our-project-1
git pull origin main
```

### 7.2 Rebuild and Restart

```bash
# Stop bot
docker-compose down

# Rebuild with new code
docker-compose up -d --build

# Verify
docker-compose logs -f crypto_bot
```

### 7.3 Zero-Downtime Update (Advanced)

For critical deployments:

```bash
# Start new container alongside old one
docker-compose up -d --scale crypto_bot=2

# Wait for new container to be healthy
# Then remove old container
docker-compose up -d --scale crypto_bot=1
```

## Emergency Procedures

### Emergency Stop

```bash
# Stop all trading immediately
docker-compose down

# Or via API
curl -X POST -H "X-API-Key: YOUR_KEY" http://localhost:8889/emergency-stop
```

### Close All Positions Manually

```bash
# Get positions
curl -H "X-API-Key: YOUR_KEY" http://localhost:8889/positions

# Close each position via API or Binance.US web interface
```

## Best Practices

1. **Always test in paper trading mode first**
2. **Start with small capital** (under $1000)
3. **Monitor daily** for the first week
4. **Keep dashboard credentials secure**
5. **Enable 2FA** on Binance account
6. **Set up alerts** for unusual activity
7. **Have an emergency plan** ready
8. **Don't over-optimize** - simple strategies often work best
9. **Document all changes** you make
10. **Stay updated** with bot and exchange changes

## Resources

- Binance.US API Docs: https://docs.binance.us/
- Docker Docs: https://docs.docker.com/
- UFW Firewall Guide: https://help.ubuntu.com/community/UFW

## Current Deployment

**VPS IP**: 207.246.99.168  
**API Port**: 8889  
**Status**: ✅ Live, Connected to Binance.US  
**Mode**: Live Trading  
**Last Updated**: October 5, 2025

---

**Remember**: Always prioritize security and risk management over profit optimization.
