#!/bin/bash
# VPS Deployment Script for ChatGPT-5 Pro Enhanced Crypto Trading Bot
# ==================================================================
# This script deploys the enhanced trading bot directly to a VPS without Docker

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration - Update these with your VPS details
VPS_IP="207.246.99.108"
VPS_USER="root"
DEPLOY_PATH="/opt/crypto-bot"
PROJECT_NAME="Our-project-1"
GIT_REPO="https://github.com/worldpath/Our-project-1.git"
BRANCH="chatgpt5-pro-enhancements"

# Functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}❌ [ERROR]${NC} $1"
    exit 1
}

warn() {
    echo -e "${YELLOW}⚠️  [WARNING]${NC} $1"
}

info() {
    echo -e "${BLUE}ℹ️  [INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Function to run commands on VPS
run_on_vps() {
    ssh -o ConnectTimeout=10 "${VPS_USER}@${VPS_IP}" "$1"
}

# Check VPS connectivity
check_vps_connection() {
    log "Testing VPS connection..."
    
    if ping -c 3 "${VPS_IP}" > /dev/null 2>&1; then
        success "Network connectivity to ${VPS_IP} OK"
    else
        error "Cannot reach ${VPS_IP}"
    fi
    
    if ssh -o ConnectTimeout=10 -o BatchMode=yes "${VPS_USER}@${VPS_IP}" "echo 'SSH OK'" > /dev/null 2>&1; then
        success "SSH connectivity OK"
    else
        error "SSH connection failed. Please check your SSH key setup."
    fi
}

# Install prerequisites on VPS
install_prerequisites() {
    log "Installing prerequisites on VPS..."
    
    run_on_vps "apt-get update -y"
    run_on_vps "apt-get install -y python3 python3-pip python3-venv git curl supervisor nginx"
    
    success "Prerequisites installed"
}

# Clone/update repository
setup_repository() {
    log "Setting up repository on VPS..."
    
    # Check if directory exists
    if run_on_vps "test -d ${DEPLOY_PATH}/.git"; then
        info "Repository exists, updating..."
        run_on_vps "cd ${DEPLOY_PATH} && git fetch origin && git checkout ${BRANCH} && git pull origin ${BRANCH}"
    else
        info "Cloning fresh repository..."
        run_on_vps "rm -rf ${DEPLOY_PATH}"
        run_on_vps "git clone -b ${BRANCH} ${GIT_REPO} ${DEPLOY_PATH}"
    fi
    
    success "Repository setup complete"
}

# Setup Python environment
setup_python_environment() {
    log "Setting up Python environment..."
    
    run_on_vps "cd ${DEPLOY_PATH} && python3 -m venv .venv"
    run_on_vps "cd ${DEPLOY_PATH} && .venv/bin/pip install --upgrade pip"
    run_on_vps "cd ${DEPLOY_PATH} && .venv/bin/pip install -r requirements.txt"
    
    success "Python environment ready"
}

# Create .env file with API credentials
setup_environment_file() {
    log "Setting up environment configuration..."
    
    # Create .env file with API credentials
    run_on_vps "cat > ${DEPLOY_PATH}/.env << EOL
BINANCE_API_KEY=***
BINANCE_API_SECRET=***
ENVIRONMENT=production
EOL"
    
    warn "Please update ${DEPLOY_PATH}/.env with your actual API credentials"
    
    success "Environment file created"
}

# Setup supervisor for service management
setup_supervisor() {
    log "Setting up supervisor services..."
    
    # Copy supervisor configurations
    run_on_vps "cp ${DEPLOY_PATH}/supervisord_enhanced_bot.conf /etc/supervisor/conf.d/crypto-bot.conf"
    run_on_vps "cp ${DEPLOY_PATH}/supervisord_control_ui.conf /etc/supervisor/conf.d/crypto-bot-ui.conf"
    
    # Update supervisor and start services
    run_on_vps "supervisorctl reread"
    run_on_vps "supervisorctl update"
    
    success "Supervisor configured"
}

# Start services
start_services() {
    log "Starting services..."
    
    # Start enhanced bot
    run_on_vps "supervisorctl start enhanced-crypto-bot"
    
    # Start control UI
    run_on_vps "supervisorctl start crypto-bot-ui"
    
    # Wait for services to start
    sleep 10
    
    # Check service status
    if run_on_vps "supervisorctl status enhanced-crypto-bot | grep RUNNING"; then
        success "Enhanced crypto bot started successfully"
    else
        error "Enhanced crypto bot failed to start"
    fi
    
    if run_on_vps "supervisorctl status crypto-bot-ui | grep RUNNING"; then
        success "Control UI started successfully"
    else
        warn "Control UI may not be running - check logs"
    fi
}

# Setup nginx proxy (optional)
setup_nginx() {
    log "Setting up Nginx reverse proxy..."
    
    # Create nginx configuration
    run_on_vps "cat > /etc/nginx/sites-available/crypto-bot << 'EOF'
server {
    listen 80;
    server_name ${VPS_IP};
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /api/ {
        proxy_pass http://localhost:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF"
    
    # Enable site
    run_on_vps "ln -sf /etc/nginx/sites-available/crypto-bot /etc/nginx/sites-enabled/"
    run_on_vps "nginx -t && systemctl reload nginx"
    
    success "Nginx configured"
}

# Run health checks
run_health_checks() {
    log "Running health checks..."
    
    sleep 15  # Give services more time to start
    
    # Check if enhanced bot is responding
    if run_on_vps "curl -f http://localhost:5000/health 2>/dev/null"; then
        success "Enhanced bot health check passed"
    else
        warn "Enhanced bot health check failed - checking logs..."
        run_on_vps "supervisorctl tail enhanced-crypto-bot"
    fi
    
    # Check if control UI is responding
    if run_on_vps "curl -f http://localhost:8000 2>/dev/null"; then
        success "Control UI health check passed"
    else
        warn "Control UI health check failed - may still be starting"
    fi
    
    success "Health checks completed"
}

# Display deployment summary
deployment_summary() {
    log "📋 Deployment Summary"
    echo "=============================="
    echo "VPS IP: ${VPS_IP}"
    echo "Deploy Path: ${DEPLOY_PATH}"
    echo "Branch: ${BRANCH}"
    echo ""
    echo "🌐 Access Points:"
    echo "  - Control UI: http://${VPS_IP}:8000"
    echo "  - API Health: http://${VPS_IP}:5000/health"
    echo "  - Nginx Proxy: http://${VPS_IP} (if configured)"
    echo ""
    echo "📋 Management Commands:"
    echo "  - Check status: ssh ${VPS_USER}@${VPS_IP} 'supervisorctl status'"
    echo "  - View logs: ssh ${VPS_USER}@${VPS_IP} 'supervisorctl tail -f enhanced-crypto-bot'"
    echo "  - Restart bot: ssh ${VPS_USER}@${VPS_IP} 'supervisorctl restart enhanced-crypto-bot'"
    echo "  - Restart UI: ssh ${VPS_USER}@${VPS_IP} 'supervisorctl restart crypto-bot-ui'"
    echo ""
    echo "🔧 Configuration Files:"
    echo "  - Environment: ${DEPLOY_PATH}/.env"
    echo "  - Supervisor: /etc/supervisor/conf.d/crypto-bot*.conf"
    echo "  - Nginx: /etc/nginx/sites-available/crypto-bot"
    echo ""
    echo "⚠️  IMPORTANT:"
    echo "  - Update ${DEPLOY_PATH}/.env with your actual API credentials"
    echo "  - This is LIVE TRADING with REAL MONEY ($3,797.84 portfolio)"
    echo "  - Monitor closely, especially in first hours"
    echo ""
    success "Deployment completed successfully! 🎉"
}

# Main deployment function
main() {
    echo "🚀 ChatGPT-5 Pro Enhanced Crypto Trading Bot VPS Deployment"
    echo "==========================================================="
    echo "VPS: ${VPS_IP}"
    echo "User: ${VPS_USER}"
    echo "Path: ${DEPLOY_PATH}"
    echo "Branch: ${BRANCH}"
    echo ""
    
    # Deployment steps
    check_vps_connection
    install_prerequisites
    setup_repository
    setup_python_environment
    setup_environment_file
    setup_supervisor
    start_services
    setup_nginx
    run_health_checks
    deployment_summary
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --vps-ip)
            VPS_IP="$2"
            shift 2
            ;;
        --vps-user)
            VPS_USER="$2"
            shift 2
            ;;
        --deploy-path)
            DEPLOY_PATH="$2"
            shift 2
            ;;
        --branch)
            BRANCH="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --vps-ip IP         VPS IP address (default: 207.246.99.108)"
            echo "  --vps-user USER     VPS user (default: root)"
            echo "  --deploy-path PATH  Deployment path (default: /opt/crypto-bot)"
            echo "  --branch BRANCH     Git branch (default: chatgpt5-pro-enhancements)"
            echo "  --help              Show this help message"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            ;;
    esac
done

# Run main deployment
main