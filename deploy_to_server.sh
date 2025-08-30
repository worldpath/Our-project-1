#!/bin/bash
# Crypto Bot Deployment Script for Vultr Server
# ==============================================
# This script deploys the crypto bot to the production server with all enhancements

set -e  # Exit on any error

# Configuration
SERVER_IP="${SERVER_IP:-207.246.99.108}"
DEPLOY_USER="${DEPLOY_USER:-ubuntu}"
DEPLOY_PATH="${DEPLOY_PATH:-/opt/crypto-bot}"
BACKUP_PATH="${BACKUP_PATH:-/opt/backups}"
SERVICE_NAME="crypto-bot"
DASHBOARD_SERVICE="crypto-bot-dashboard"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to run commands on remote server
run_remote() {
    ssh -o ConnectTimeout=10 "${DEPLOY_USER}@${SERVER_IP}" "$1"
}

# Function to copy files to remote server
copy_to_remote() {
    scp -r "$1" "${DEPLOY_USER}@${SERVER_IP}:$2"
}

# Check if we can connect to the server
check_connectivity() {
    log "🔌 Testing connectivity to ${SERVER_IP}..."
    
    if ping -c 3 "${SERVER_IP}" > /dev/null 2>&1; then
        success "Network connectivity to ${SERVER_IP} OK"
    else
        error "Cannot reach ${SERVER_IP}"
        exit 1
    fi
    
    if ssh -o ConnectTimeout=10 -o BatchMode=yes "${DEPLOY_USER}@${SERVER_IP}" "echo 'SSH OK'" > /dev/null 2>&1; then
        success "SSH connectivity OK"
    else
        error "SSH connection failed. Please check your SSH key setup."
        exit 1
    fi
}

# Create backup of current deployment
create_backup() {
    log "💾 Creating backup of current deployment..."
    
    BACKUP_NAME="crypto-bot-backup-$(date +'%Y%m%d-%H%M%S')"
    
    run_remote "sudo mkdir -p ${BACKUP_PATH}"
    
    # Stop services before backup
    run_remote "sudo systemctl stop ${SERVICE_NAME} || true"
    run_remote "sudo systemctl stop ${DASHBOARD_SERVICE} || true"
    
    # Create backup
    run_remote "sudo cp -r ${DEPLOY_PATH} ${BACKUP_PATH}/${BACKUP_NAME} || true"
    
    success "Backup created: ${BACKUP_PATH}/${BACKUP_NAME}"
}

# Deploy application files
deploy_files() {
    log "📁 Deploying application files..."
    
    # Create deployment directory
    run_remote "sudo mkdir -p ${DEPLOY_PATH}"
    run_remote "sudo chown ${DEPLOY_USER}:${DEPLOY_USER} ${DEPLOY_PATH}"
    
    # Copy application files
    log "Copying application files..."
    copy_to_remote "." "${DEPLOY_PATH}/"
    
    # Set permissions
    run_remote "chmod +x ${DEPLOY_PATH}/*.py"
    run_remote "chmod +x ${DEPLOY_PATH}/deploy_to_server.sh"
    
    success "Application files deployed"
}

# Setup Python environment
setup_python_env() {
    log "🐍 Setting up Python environment..."
    
    # Check if Python 3.8+ is available
    run_remote "python3 --version"
    
    # Create virtual environment
    run_remote "cd ${DEPLOY_PATH} && python3 -m venv .venv"
    
    # Upgrade pip
    run_remote "cd ${DEPLOY_PATH} && .venv/bin/pip install --upgrade pip"
    
    # Install requirements
    run_remote "cd ${DEPLOY_PATH} && .venv/bin/pip install -r requirements.txt"
    
    success "Python environment setup complete"
}

# Configure environment variables
configure_environment() {
    log "⚙️  Configuring environment..."
    
    # Check if .env exists, if not create from example
    if ! run_remote "test -f ${DEPLOY_PATH}/.env"; then
        warning ".env file not found, creating from .env.example"
        run_remote "cd ${DEPLOY_PATH} && cp .env.example .env"
        warning "Please edit ${DEPLOY_PATH}/.env with your API keys and configuration"
    else
        success ".env file exists"
    fi
    
    # Set proper permissions for .env
    run_remote "chmod 600 ${DEPLOY_PATH}/.env"
}

# Setup systemd services
setup_services() {
    log "🔧 Setting up systemd services..."
    
    # Copy service files
    run_remote "sudo cp ${DEPLOY_PATH}/deploy/systemd/crypto-bot.service /etc/systemd/system/"
    run_remote "sudo cp ${DEPLOY_PATH}/deploy/systemd/crypto-bot-dashboard.service /etc/systemd/system/"
    
    # Reload systemd
    run_remote "sudo systemctl daemon-reload"
    
    # Enable services
    run_remote "sudo systemctl enable ${SERVICE_NAME}"
    run_remote "sudo systemctl enable ${DASHBOARD_SERVICE}"
    
    success "Systemd services configured"
}

# Setup nginx/caddy (optional)
setup_web_proxy() {
    log "🌐 Setting up web proxy..."
    
    # Check if nginx or caddy is available
    if run_remote "command -v nginx > /dev/null 2>&1"; then
        log "Nginx detected, configuring nginx proxy..."
        run_remote "sudo cp ${DEPLOY_PATH}/deploy/nginx/crypto-bot.conf /etc/nginx/sites-available/"
        run_remote "sudo ln -sf /etc/nginx/sites-available/crypto-bot.conf /etc/nginx/sites-enabled/"
        run_remote "sudo nginx -t && sudo systemctl reload nginx"
        success "Nginx configured"
    elif run_remote "command -v caddy > /dev/null 2>&1"; then
        log "Caddy detected, configuring caddy proxy..."
        run_remote "sudo cp ${DEPLOY_PATH}/deploy/caddy/Caddyfile /etc/caddy/"
        run_remote "sudo systemctl reload caddy"
        success "Caddy configured"
    else
        warning "No web proxy (nginx/caddy) detected - services will run on direct ports"
    fi
}

# Run startup validation
run_startup_validation() {
    log "✅ Running startup validation..."
    
    run_remote "cd ${DEPLOY_PATH} && .venv/bin/python startup_system.py --health-check"
    
    success "Startup validation passed"
}

# Start services
start_services() {
    log "🚀 Starting services..."
    
    # Start dashboard first
    run_remote "sudo systemctl start ${DASHBOARD_SERVICE}"
    sleep 5
    
    # Start main trading service
    run_remote "sudo systemctl start ${SERVICE_NAME}"
    sleep 10
    
    # Check service status
    if run_remote "sudo systemctl is-active ${SERVICE_NAME} > /dev/null 2>&1"; then
        success "Trading service started successfully"
    else
        error "Trading service failed to start"
        run_remote "sudo journalctl -u ${SERVICE_NAME} -n 20"
        exit 1
    fi
    
    if run_remote "sudo systemctl is-active ${DASHBOARD_SERVICE} > /dev/null 2>&1"; then
        success "Dashboard service started successfully"
    else
        error "Dashboard service failed to start"
        run_remote "sudo journalctl -u ${DASHBOARD_SERVICE} -n 20"
        exit 1
    fi
}

# Run health checks
run_health_checks() {
    log "🔍 Running health checks..."
    
    # Check if services are responding
    sleep 30  # Give services time to start
    
    # Test dashboard endpoint
    if run_remote "curl -f http://localhost:8000/healthz > /dev/null 2>&1"; then
        success "Dashboard health check passed"
    else
        warning "Dashboard health check failed"
    fi
    
    # Run comprehensive health check
    run_remote "cd ${DEPLOY_PATH} && .venv/bin/python deployment_health_check.py --server localhost > health_check_results.json"
    
    success "Health checks completed - see health_check_results.json on server"
}

# Setup monitoring and maintenance
setup_monitoring() {
    log "📊 Setting up monitoring and maintenance..."
    
    # Setup log rotation
    cat << 'EOF' | run_remote "sudo tee /etc/logrotate.d/crypto-bot"
/opt/crypto-bot/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 ubuntu ubuntu
    postrotate
        systemctl reload crypto-bot crypto-bot-dashboard 2>/dev/null || true
    endscript
}
EOF

    # Setup daily backup cron job
    run_remote "echo '0 2 * * * cd ${DEPLOY_PATH} && .venv/bin/python backup_system.py --create daily' | crontab -"
    
    success "Monitoring and maintenance configured"
}

# Display deployment summary
deployment_summary() {
    log "📋 Deployment Summary"
    echo "=============================="
    echo "Server IP: ${SERVER_IP}"
    echo "Deploy Path: ${DEPLOY_PATH}"
    echo "Services:"
    echo "  - ${SERVICE_NAME}"
    echo "  - ${DASHBOARD_SERVICE}"
    echo ""
    echo "🌐 Access Points:"
    echo "  - Dashboard: http://${SERVER_IP}:8000"
    echo "  - Health Check: http://${SERVER_IP}:8000/healthz"
    echo ""
    echo "📋 Management Commands:"
    echo "  - Check status: sudo systemctl status ${SERVICE_NAME}"
    echo "  - View logs: sudo journalctl -u ${SERVICE_NAME} -f"
    echo "  - Restart: sudo systemctl restart ${SERVICE_NAME}"
    echo ""
    echo "🔧 Configuration Files:"
    echo "  - Environment: ${DEPLOY_PATH}/.env"
    echo "  - Configuration: ${DEPLOY_PATH}/config/aggressive_production.yaml"
    echo ""
    success "Deployment completed successfully! 🎉"
}

# Main deployment function
main() {
    echo "🚀 Crypto Bot Production Deployment"
    echo "==================================="
    echo "Server: ${SERVER_IP}"
    echo "User: ${DEPLOY_USER}"
    echo "Path: ${DEPLOY_PATH}"
    echo ""
    
    # Deployment steps
    check_connectivity
    create_backup
    deploy_files
    setup_python_env
    configure_environment
    setup_services
    setup_web_proxy
    run_startup_validation
    start_services
    run_health_checks
    setup_monitoring
    deployment_summary
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --server-ip)
            SERVER_IP="$2"
            shift 2
            ;;
        --deploy-user)
            DEPLOY_USER="$2"
            shift 2
            ;;
        --deploy-path)
            DEPLOY_PATH="$2"
            shift 2
            ;;
        --no-backup)
            SKIP_BACKUP=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --server-ip IP      Server IP address (default: 207.246.99.108)"
            echo "  --deploy-user USER  Deployment user (default: ubuntu)"
            echo "  --deploy-path PATH  Deployment path (default: /opt/crypto-bot)"
            echo "  --no-backup         Skip backup creation"
            echo "  --help              Show this help message"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main deployment
main