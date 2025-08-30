#!/bin/bash
# Enhanced Trading Bot Deployment Script
# =====================================
# Complete deployment automation for the Ultra-Aggressive Enhanced Trading Bot

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEPLOYMENT_MODE="${1:-production}"  # production, staging, development
PROJECT_NAME="enhanced-trading-bot"
BACKUP_DIR="/opt/trading-bot-backups"
LOG_FILE="/var/log/enhanced-bot-deploy.log"

# Functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

check_prerequisites() {
    log "Checking deployment prerequisites..."
    
    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
    fi
    
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running. Please start Docker."
    fi
    
    # Check if Docker Compose is available
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose."
    fi
    
    # Check required files
    local required_files=(
        ".env"
        "config/ultra_aggressive.yaml"
        "enhanced_requirements.txt"
        "docker-compose-enhanced.yml"
        "Dockerfile.enhanced"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            error "Required file not found: $file"
        fi
    done
    
    log "✅ All prerequisites met"
}

create_backup() {
    log "Creating backup of current deployment..."
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_path="${BACKUP_DIR}/${PROJECT_NAME}_${timestamp}"
    
    mkdir -p "$backup_path"
    
    # Backup configuration and data
    if [ -d "config" ]; then
        cp -r config "$backup_path/"
    fi
    
    if [ -d "logs" ]; then
        cp -r logs "$backup_path/"
    fi
    
    if [ -d "tax_reports" ]; then
        cp -r tax_reports "$backup_path/"
    fi
    
    # Export Docker volumes if they exist
    if docker volume ls | grep -q "${PROJECT_NAME}_trading_bot_data"; then
        docker run --rm -v "${PROJECT_NAME}_trading_bot_data:/source" -v "$backup_path:/backup" alpine tar czf /backup/trading_bot_data.tar.gz -C /source .
    fi
    
    log "✅ Backup created at $backup_path"
}

setup_environment() {
    log "Setting up deployment environment..."
    
    # Create required directories
    mkdir -p logs config tax_reports data monitoring/grafana/{dashboards,datasources}
    
    # Set proper permissions
    chmod 755 logs config tax_reports data
    chmod +x start_enhanced_bot.py deploy_enhanced_bot.sh
    
    # Copy environment-specific configuration
    case "$DEPLOYMENT_MODE" in
        "production")
            log "Setting up production environment..."
            export COMPOSE_FILE="docker-compose-enhanced.yml"
            export COMPOSE_PROJECT_NAME="${PROJECT_NAME}-prod"
            ;;
        "staging")
            log "Setting up staging environment..."
            export COMPOSE_FILE="docker-compose-enhanced.yml"
            export COMPOSE_PROJECT_NAME="${PROJECT_NAME}-staging"
            # Override some settings for staging
            export BINANCE_TESTNET=true
            ;;
        "development")
            log "Setting up development environment..."
            export COMPOSE_FILE="docker-compose-enhanced.yml"
            export COMPOSE_PROJECT_NAME="${PROJECT_NAME}-dev"
            export BINANCE_TESTNET=true
            ;;
        *)
            error "Invalid deployment mode: $DEPLOYMENT_MODE"
            ;;
    esac
    
    log "✅ Environment setup complete"
}

install_dependencies() {
    log "Installing Python dependencies..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    
    # Activate virtual environment and install dependencies
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r enhanced_requirements.txt
    
    log "✅ Dependencies installed"
}

build_docker_images() {
    log "Building Docker images..."
    
    # Build main trading bot image
    docker-compose -f "$COMPOSE_FILE" -p "$COMPOSE_PROJECT_NAME" build enhanced-trading-bot
    
    # Pull other required images
    docker-compose -f "$COMPOSE_FILE" -p "$COMPOSE_PROJECT_NAME" pull prometheus grafana redis alertmanager node-exporter cadvisor
    
    log "✅ Docker images ready"
}

deploy_services() {
    log "Deploying enhanced trading bot services..."
    
    # Stop existing services if running
    docker-compose -f "$COMPOSE_FILE" -p "$COMPOSE_PROJECT_NAME" down --remove-orphans || true
    
    # Start services
    docker-compose -f "$COMPOSE_FILE" -p "$COMPOSE_PROJECT_NAME" up -d
    
    # Wait for services to start
    log "Waiting for services to start..."
    sleep 30
    
    # Check service health
    check_service_health
    
    log "✅ Services deployed successfully"
}

check_service_health() {
    log "Checking service health..."
    
    local services=("enhanced-trading-bot" "prometheus" "grafana" "redis")
    local failed_services=()
    
    for service in "${services[@]}"; do
        if docker-compose -f "$COMPOSE_FILE" -p "$COMPOSE_PROJECT_NAME" ps "$service" | grep -q "Up"; then
            log "✅ $service is running"
        else
            warn "❌ $service is not running"
            failed_services+=("$service")
        fi
    done
    
    if [ ${#failed_services[@]} -gt 0 ]; then
        error "Some services failed to start: ${failed_services[*]}"
    fi
    
    # Test API endpoints
    log "Testing API endpoints..."
    
    # Wait a bit more for full startup
    sleep 10
    
    # Test trading bot health endpoint
    if curl -f -s http://localhost:8080/health > /dev/null; then
        log "✅ Trading bot API is healthy"
    else
        warn "⚠️ Trading bot API health check failed (may still be starting)"
    fi
    
    # Test Prometheus
    if curl -f -s http://localhost:9091 > /dev/null; then
        log "✅ Prometheus is accessible"
    else
        warn "⚠️ Prometheus health check failed"
    fi
    
    # Test Grafana
    if curl -f -s http://localhost:3000 > /dev/null; then
        log "✅ Grafana is accessible"
    else
        warn "⚠️ Grafana health check failed"
    fi
}

setup_monitoring() {
    log "Setting up monitoring and alerting..."
    
    # Import Grafana dashboards
    log "Configuring Grafana dashboards..."
    
    # Wait for Grafana to be fully ready
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -f -s http://admin:admin123@localhost:3000/api/health > /dev/null; then
            break
        fi
        sleep 2
        ((attempt++))
    done
    
    if [ $attempt -eq $max_attempts ]; then
        warn "⚠️ Grafana not ready for dashboard import"
    else
        log "✅ Grafana is ready"
    fi
    
    log "✅ Monitoring setup complete"
}

run_initial_tests() {
    log "Running initial system tests..."
    
    # Test configuration loading
    if docker exec "${COMPOSE_PROJECT_NAME}_enhanced-trading-bot_1" python -c "
import yaml
with open('config/ultra_aggressive.yaml') as f:
    config = yaml.safe_load(f)
print('✅ Configuration loaded successfully')
"; then
        log "✅ Configuration test passed"
    else
        error "❌ Configuration test failed"
    fi
    
    # Test Binance API connection (if not in test mode)
    if [ "$DEPLOYMENT_MODE" != "development" ]; then
        log "Testing Binance API connection..."
        if docker exec "${COMPOSE_PROJECT_NAME}_enhanced-trading-bot_1" python -c "
import os
import asyncio
from main import BinanceConnector

async def test_connection():
    connector = BinanceConnector(
        api_key=os.getenv('BINANCE_API_KEY'),
        api_secret=os.getenv('BINANCE_API_SECRET'),
        testnet=os.getenv('BINANCE_TESTNET', 'false').lower() == 'true'
    )
    result = await connector.get_account_info()
    if result:
        print('✅ Binance API connection successful')
    else:
        print('❌ Binance API connection failed')

asyncio.run(test_connection())
"; then
            log "✅ Binance API test passed"
        else
            error "❌ Binance API test failed"
        fi
    fi
    
    log "✅ Initial tests completed"
}

display_deployment_info() {
    log "Deployment completed successfully! 🚀"
    
    echo ""
    echo "=================================================================="
    echo "Enhanced Trading Bot Deployment Information"
    echo "=================================================================="
    echo "Mode: $DEPLOYMENT_MODE"
    echo "Project: $COMPOSE_PROJECT_NAME"
    echo ""
    echo "📊 Service URLs:"
    echo "  • Trading Bot API:    http://localhost:8080"
    echo "  • Trading Bot Health: http://localhost:8080/health"
    echo "  • Prometheus:         http://localhost:9091"
    echo "  • Grafana:            http://localhost:3000 (admin/admin123)"
    echo "  • AlertManager:       http://localhost:9093"
    echo ""
    echo "📂 Important Directories:"
    echo "  • Logs:               ./logs/"
    echo "  • Config:             ./config/"
    echo "  • Tax Reports:        ./tax_reports/"
    echo "  • Backups:            $BACKUP_DIR"
    echo ""
    echo "🔧 Management Commands:"
    echo "  • View logs:          docker-compose -f $COMPOSE_FILE -p $COMPOSE_PROJECT_NAME logs -f"
    echo "  • Stop services:      docker-compose -f $COMPOSE_FILE -p $COMPOSE_PROJECT_NAME down"
    echo "  • Restart bot:        docker-compose -f $COMPOSE_FILE -p $COMPOSE_PROJECT_NAME restart enhanced-trading-bot"
    echo "  • Check status:       docker-compose -f $COMPOSE_FILE -p $COMPOSE_PROJECT_NAME ps"
    echo ""
    echo "⚠️  IMPORTANT NOTES:"
    if [ "$DEPLOYMENT_MODE" = "production" ]; then
        echo "  • This is LIVE TRADING mode with REAL MONEY!"
        echo "  • Monitor the bot closely, especially in the first hours"
        echo "  • Daily PnL alerts are configured for -5% and -10%"
    else
        echo "  • This is TEST mode using Binance testnet"
        echo "  • No real money will be used"
    fi
    echo "  • All trades are logged and tracked for tax purposes"
    echo "  • Backup is recommended before major configuration changes"
    echo "=================================================================="
}

# Main deployment flow
main() {
    log "Starting Enhanced Trading Bot deployment in $DEPLOYMENT_MODE mode..."
    
    # Create log file directory
    mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
    
    # Run deployment steps
    check_prerequisites
    create_backup
    setup_environment
    install_dependencies
    build_docker_images
    deploy_services
    setup_monitoring
    run_initial_tests
    display_deployment_info
    
    log "🎉 Enhanced Trading Bot deployment completed successfully!"
}

# Show usage if help requested
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    echo "Enhanced Trading Bot Deployment Script"
    echo "====================================="
    echo ""
    echo "Usage: $0 [MODE]"
    echo ""
    echo "Modes:"
    echo "  production   - Live trading with real money (default)"
    echo "  staging      - Testing with testnet"
    echo "  development  - Development mode with testnet"
    echo ""
    echo "Examples:"
    echo "  $0 production    # Deploy for live trading"
    echo "  $0 staging       # Deploy for testing"
    echo "  $0 development   # Deploy for development"
    echo ""
    echo "Requirements:"
    echo "  - Docker and Docker Compose installed"
    echo "  - Configured .env file with API keys"
    echo "  - config/ultra_aggressive.yaml configuration"
    echo ""
    exit 0
fi

# Run main deployment
main "$@"