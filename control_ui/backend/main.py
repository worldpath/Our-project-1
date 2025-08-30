#!/usr/bin/env python3
"""
Ultra-Aggressive Crypto Bot Control Plane
==========================================
Modern FastAPI-based control interface for monitoring and controlling the crypto trading bot.
Based on ChatGPT-5 Pro recommendations for performance, stability and tax reporting.
"""

import asyncio
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# Local imports
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../bot_enhancements'))
from risk_constraints import RiskConfig, Profile

# Initialize FastAPI app
app = FastAPI(title="Crypto Bot Control Plane", version="2.0.0")

# Setup static files and templates
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND_DIR / "static"), name="static")
templates = Jinja2Templates(directory=FRONTEND_DIR / "templates")

# WebSocket connections for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                self.disconnect(connection)

manager = ConnectionManager()

# Data models
class RiskSettings(BaseModel):
    profile: Profile
    portfolio_risk: float
    max_position_size: float
    risk_per_trade: float
    max_daily_loss: float
    max_drawdown: float
    max_concurrent_positions: int
    consecutive_loss_kill: int

class TradingSettings(BaseModel):
    min_volume_usd: float = 50_000.0  # $50k minimum 24h volume (ensures liquidity for small trades)
    max_spread_bps: float = 25.0
    top_n_symbols: int = 30
    tp_percent: float = 2.0
    sl_percent: float = 1.0
    trailing_stop_percent: float = 0.5
    strategy_weights: Dict[str, float] = {"momentum": 0.4, "mean_reversion": 0.3, "breakout": 0.3}

class BotMetrics(BaseModel):
    portfolio_value: float = 0.0
    realized_pnl_24h: float = 0.0
    unrealized_pnl: float = 0.0
    exposure_percent: float = 0.0
    heat_percent: float = 0.0
    win_rate: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    rate_limit_remaining: int = 1200
    active_positions: int = 0
    total_trades_24h: int = 0
    uptime_hours: float = 0.0
    last_updated: datetime = datetime.now()

# Global state
current_metrics = BotMetrics()
current_risk_settings = RiskSettings(
    profile="moderate",
    portfolio_risk=25.0,
    max_position_size=10.0,
    risk_per_trade=1.5,
    max_daily_loss=5.0,
    max_drawdown=25.0,
    max_concurrent_positions=5,
    consecutive_loss_kill=7
)
current_trading_settings = TradingSettings()

# Bot integration stub - replace with actual IPC
def apply_settings_to_bot(settings: dict) -> bool:
    """
    Stub for applying settings to the actual bot.
    Replace this with your actual IPC mechanism (Redis, HTTP, file, etc.)
    """
    try:
        # Write settings to file that bot can monitor
        bot_control_file = Path(__file__).parent.parent.parent / "bot_control.json"
        with open(bot_control_file, 'w') as f:
            json.dump(settings, f, indent=2, default=str)
        
        # TODO: Replace with actual bot integration:
        # - Redis pub/sub: redis_client.publish('bot_settings', json.dumps(settings))
        # - HTTP call: requests.post('http://localhost:8001/settings', json=settings)
        # - PostgreSQL NOTIFY: cursor.execute("NOTIFY bot_settings, %s", (json.dumps(settings),))
        
        return True
    except Exception as e:
        logging.error(f"Failed to apply settings to bot: {e}")
        return False

# Routes
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "bot_name": "Ultra-Aggressive Crypto Bot",
        "version": "2.0.0"
    })

@app.get("/api/metrics")
async def get_metrics() -> BotMetrics:
    """Get current bot metrics"""
    # In real implementation, fetch from bot's metrics endpoint or database
    return current_metrics

@app.get("/api/risk-settings")
async def get_risk_settings() -> RiskSettings:
    """Get current risk settings"""
    return current_risk_settings

@app.get("/api/trading-settings")
async def get_trading_settings() -> TradingSettings:
    """Get current trading settings"""
    return current_trading_settings

@app.post("/api/risk-settings")
async def update_risk_settings(settings: RiskSettings):
    """Update risk settings and apply to bot"""
    try:
        # Validate settings using ChatGPT-5 Pro constraints
        risk_config = RiskConfig(
            profile=settings.profile,
            portfolio_risk=settings.portfolio_risk,
            max_position_size=settings.max_position_size,
            risk_per_trade=settings.risk_per_trade,
            max_daily_loss=settings.max_daily_loss,
            max_drawdown=settings.max_drawdown,
            max_concurrent_positions=settings.max_concurrent_positions,
            consecutive_loss_kill=settings.consecutive_loss_kill
        )
        
        # Apply validated settings
        global current_risk_settings
        current_risk_settings = RiskSettings(**risk_config.dict())
        
        # Send to bot
        success = apply_settings_to_bot({"risk": current_risk_settings.dict()})
        
        if success:
            # Broadcast to WebSocket clients
            await manager.broadcast({
                "type": "risk_settings_updated", 
                "data": current_risk_settings.dict()
            })
            return {"success": True, "message": "Risk settings updated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to apply settings to bot")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/trading-settings")
async def update_trading_settings(settings: TradingSettings):
    """Update trading settings and apply to bot"""
    try:
        global current_trading_settings
        current_trading_settings = settings
        
        # Send to bot
        success = apply_settings_to_bot({"trading": settings.dict()})
        
        if success:
            await manager.broadcast({
                "type": "trading_settings_updated", 
                "data": settings.dict()
            })
            return {"success": True, "message": "Trading settings updated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to apply settings to bot")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/emergency-stop")
async def emergency_stop():
    """Emergency stop all trading"""
    success = apply_settings_to_bot({"emergency_stop": True})
    if success:
        await manager.broadcast({"type": "emergency_stop", "data": {}})
        return {"success": True, "message": "Emergency stop activated"}
    else:
        raise HTTPException(status_code=500, detail="Failed to stop bot")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Send periodic updates
            await asyncio.sleep(1)
            await websocket.send_text(json.dumps({
                "type": "metrics_update",
                "data": current_metrics.dict()
            }))
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Background task to simulate metrics updates
async def update_metrics():
    """Background task to update metrics (replace with real bot data)"""
    while True:
        await asyncio.sleep(5)
        # TODO: Fetch real metrics from bot
        global current_metrics
        current_metrics.last_updated = datetime.now()
        current_metrics.uptime_hours += 5/3600  # Add 5 seconds
        
        await manager.broadcast({
            "type": "metrics_update",
            "data": current_metrics.dict()
        })

@app.on_event("startup")
async def startup_event():
    """Start background tasks"""
    asyncio.create_task(update_metrics())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)