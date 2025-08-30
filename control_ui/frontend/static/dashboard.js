// Dashboard JavaScript for Ultra-Aggressive Crypto Bot Control Plane
// Enhanced with ChatGPT-5 Pro recommendations for real-time control

class CryptoBotDashboard {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectInterval = 5000;
        
        this.initializeWebSocket();
        this.initializeEventListeners();
        this.loadInitialData();
    }

    initializeWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        try {
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.reconnectAttempts = 0;
                this.updateConnectionStatus(true);
            };
            
            this.ws.onmessage = (event) => {
                const message = JSON.parse(event.data);
                this.handleWebSocketMessage(message);
            };
            
            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.updateConnectionStatus(false);
                this.attemptReconnect();
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateConnectionStatus(false);
            };
        } catch (error) {
            console.error('Failed to create WebSocket:', error);
            this.updateConnectionStatus(false);
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            
            setTimeout(() => {
                this.initializeWebSocket();
            }, this.reconnectInterval);
        } else {
            console.error('Max reconnection attempts reached');
        }
    }

    handleWebSocketMessage(message) {
        switch (message.type) {
            case 'metrics_update':
                this.updateMetrics(message.data);
                break;
            case 'risk_settings_updated':
                this.showNotification('Risk settings updated successfully', 'success');
                break;
            case 'trading_settings_updated':
                this.showNotification('Trading settings updated successfully', 'success');
                break;
            case 'emergency_stop':
                this.showNotification('Emergency stop activated!', 'error');
                break;
            default:
                console.log('Unknown message type:', message.type);
        }
    }

    updateMetrics(metrics) {
        // Update portfolio value
        document.getElementById('portfolioValue').textContent = this.formatCurrency(metrics.portfolio_value);
        
        // Update 24h P&L with color coding
        const pnlElement = document.getElementById('realizedPnl');
        const pnlValue = metrics.realized_pnl_24h;
        pnlElement.textContent = this.formatCurrency(pnlValue);
        pnlElement.className = `text-3xl font-bold ${pnlValue >= 0 ? 'text-green-400' : 'text-red-400'}`;
        
        // Update other metrics
        document.getElementById('activePositions').textContent = metrics.active_positions;
        document.getElementById('winRate').textContent = `${(metrics.win_rate * 100).toFixed(1)}%`;
        document.getElementById('exposurePercent').textContent = `${metrics.exposure_percent.toFixed(1)}%`;
        document.getElementById('heatPercent').textContent = `${metrics.heat_percent.toFixed(1)}%`;
        document.getElementById('sharpeRatio').textContent = metrics.sharpe_ratio.toFixed(2);
        document.getElementById('maxDrawdown').textContent = `${metrics.max_drawdown.toFixed(1)}%`;
        document.getElementById('trades24h').textContent = metrics.total_trades_24h;
        document.getElementById('rateLimit').textContent = `${metrics.rate_limit_remaining}/1200`;
        
        // Update progress bars
        document.getElementById('exposureBar').style.width = `${Math.min(100, metrics.exposure_percent)}%`;
        document.getElementById('heatBar').style.width = `${Math.min(100, metrics.heat_percent)}%`;
        document.getElementById('rateLimitBar').style.width = `${(metrics.rate_limit_remaining / 1200) * 100}%`;
        
        // Update uptime
        const uptimeHours = Math.floor(metrics.uptime_hours);
        const uptimeMinutes = Math.floor((metrics.uptime_hours - uptimeHours) * 60);
        document.getElementById('uptime').textContent = `${uptimeHours}h ${uptimeMinutes}m`;
        
        // Update last update time
        document.getElementById('lastUpdate').textContent = new Date(metrics.last_updated).toLocaleTimeString();
    }

    initializeEventListeners() {
        // Risk settings form
        document.getElementById('riskSettingsForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.updateRiskSettings();
        });
        
        // Trading settings form
        document.getElementById('tradingSettingsForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.updateTradingSettings();
        });
        
        // Emergency stop button
        document.getElementById('emergencyStop').addEventListener('click', () => {
            this.emergencyStop();
        });
        
        // Risk profile change handler
        document.getElementById('riskProfile').addEventListener('change', (e) => {
            this.applyRiskProfile(e.target.value);
        });
    }

    async loadInitialData() {
        try {
            // Load risk settings
            const riskResponse = await fetch('/api/risk-settings');
            const riskSettings = await riskResponse.json();
            this.populateRiskSettings(riskSettings);
            
            // Load trading settings
            const tradingResponse = await fetch('/api/trading-settings');
            const tradingSettings = await tradingResponse.json();
            this.populateTradingSettings(tradingSettings);
            
            // Load initial metrics
            const metricsResponse = await fetch('/api/metrics');
            const metrics = await metricsResponse.json();
            this.updateMetrics(metrics);
            
        } catch (error) {
            console.error('Failed to load initial data:', error);
            this.showNotification('Failed to load initial data', 'error');
        }
    }

    populateRiskSettings(settings) {
        document.getElementById('riskProfile').value = settings.profile;
        document.getElementById('portfolioRisk').value = settings.portfolio_risk;
        document.getElementById('maxPositionSize').value = settings.max_position_size;
        document.getElementById('riskPerTrade').value = settings.risk_per_trade;
        document.getElementById('maxDailyLoss').value = settings.max_daily_loss;
        document.getElementById('maxDrawdown').value = settings.max_drawdown;
    }

    populateTradingSettings(settings) {
        document.getElementById('minVolumeUsd').value = settings.min_volume_usd;
        document.getElementById('maxSpreadBps').value = settings.max_spread_bps;
        document.getElementById('tpPercent').value = settings.tp_percent;
        document.getElementById('slPercent').value = settings.sl_percent;
        document.getElementById('trailingStopPercent').value = settings.trailing_stop_percent;
        document.getElementById('momentumWeight').value = settings.strategy_weights.momentum;
        document.getElementById('meanReversionWeight').value = settings.strategy_weights.mean_reversion;
        document.getElementById('breakoutWeight').value = settings.strategy_weights.breakout;
    }

    applyRiskProfile(profile) {
        // Apply preset risk configurations based on ChatGPT-5 Pro recommendations
        const presets = {
            'conservative': {
                portfolio_risk: 15,
                max_position_size: 5,
                risk_per_trade: 0.5,
                max_daily_loss: 2,
                max_drawdown: 10
            },
            'moderate': {
                portfolio_risk: 25,
                max_position_size: 10,
                risk_per_trade: 1.0,
                max_daily_loss: 5,
                max_drawdown: 20
            },
            'aggressive': {
                portfolio_risk: 35,
                max_position_size: 15,
                risk_per_trade: 2.0,
                max_daily_loss: 10,
                max_drawdown: 30
            },
            'ultra': {
                portfolio_risk: 45,
                max_position_size: 20,
                risk_per_trade: 3.0,
                max_daily_loss: 15,
                max_drawdown: 40
            }
        };
        
        const preset = presets[profile];
        if (preset) {
            document.getElementById('portfolioRisk').value = preset.portfolio_risk;
            document.getElementById('maxPositionSize').value = preset.max_position_size;
            document.getElementById('riskPerTrade').value = preset.risk_per_trade;
            document.getElementById('maxDailyLoss').value = preset.max_daily_loss;
            document.getElementById('maxDrawdown').value = preset.max_drawdown;
        }
    }

    async updateRiskSettings() {
        const settings = {
            profile: document.getElementById('riskProfile').value,
            portfolio_risk: parseFloat(document.getElementById('portfolioRisk').value),
            max_position_size: parseFloat(document.getElementById('maxPositionSize').value),
            risk_per_trade: parseFloat(document.getElementById('riskPerTrade').value),
            max_daily_loss: parseFloat(document.getElementById('maxDailyLoss').value),
            max_drawdown: parseFloat(document.getElementById('maxDrawdown').value),
            max_concurrent_positions: 15,
            consecutive_loss_kill: 8
        };
        
        try {
            const response = await fetch('/api/risk-settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(settings)
            });
            
            if (response.ok) {
                this.showNotification('Risk settings updated successfully', 'success');
            } else {
                const error = await response.json();
                throw new Error(error.detail);
            }
        } catch (error) {
            console.error('Failed to update risk settings:', error);
            this.showNotification(`Failed to update risk settings: ${error.message}`, 'error');
        }
    }

    async updateTradingSettings() {
        const settings = {
            min_volume_usd: parseFloat(document.getElementById('minVolumeUsd').value),
            max_spread_bps: parseFloat(document.getElementById('maxSpreadBps').value),
            top_n_symbols: 30,
            tp_percent: parseFloat(document.getElementById('tpPercent').value),
            sl_percent: parseFloat(document.getElementById('slPercent').value),
            trailing_stop_percent: parseFloat(document.getElementById('trailingStopPercent').value),
            strategy_weights: {
                momentum: parseFloat(document.getElementById('momentumWeight').value),
                mean_reversion: parseFloat(document.getElementById('meanReversionWeight').value),
                breakout: parseFloat(document.getElementById('breakoutWeight').value)
            }
        };
        
        try {
            const response = await fetch('/api/trading-settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(settings)
            });
            
            if (response.ok) {
                this.showNotification('Trading settings updated successfully', 'success');
            } else {
                const error = await response.json();
                throw new Error(error.detail);
            }
        } catch (error) {
            console.error('Failed to update trading settings:', error);
            this.showNotification(`Failed to update trading settings: ${error.message}`, 'error');
        }
    }

    async emergencyStop() {
        if (confirm('Are you sure you want to activate emergency stop? This will halt all trading immediately.')) {
            try {
                const response = await fetch('/api/emergency-stop', { method: 'POST' });
                if (response.ok) {
                    this.showNotification('Emergency stop activated successfully', 'success');
                } else {
                    throw new Error('Failed to activate emergency stop');
                }
            } catch (error) {
                console.error('Emergency stop failed:', error);
                this.showNotification('Failed to activate emergency stop', 'error');
            }
        }
    }

    updateConnectionStatus(connected) {
        const statusElements = document.querySelectorAll('.connection-status');
        statusElements.forEach(el => {
            el.textContent = connected ? 'Connected' : 'Disconnected';
            el.className = `connection-status ${connected ? 'text-green-400' : 'text-red-400'}`;
        });
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 transition-all duration-300 ${
            type === 'success' ? 'bg-green-600 text-white' :
            type === 'error' ? 'bg-red-600 text-white' :
            'bg-blue-600 text-white'
        }`;
        notification.textContent = message;
        
        // Add to DOM
        document.body.appendChild(notification);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 5000);
    }

    formatCurrency(value) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(value);
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new CryptoBotDashboard();
});

// Handle page visibility change to reconnect WebSocket
document.addEventListener('visibilitychange', () => {
    if (!document.hidden && window.dashboard && (!window.dashboard.ws || window.dashboard.ws.readyState !== WebSocket.OPEN)) {
        window.dashboard.initializeWebSocket();
    }
});