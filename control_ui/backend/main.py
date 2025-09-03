#!/usr/bin/env python3
"""
Enhanced Ultra-Aggressive Crypto Bot Control Plane
==================================================
Modern FastAPI-based control interface with enhanced security, authentication,
and improved bot communication for monitoring and controlling the crypto trading bot.
"""

import asyncio
import json
import os
import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, Depends, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
import jwt
from passlib.context import CryptContext

# Local imports
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../bot_enhancements'))
try:
    from risk_constraints import RiskConfig, Profile
except ImportError:
    # Fallback if risk_constraints module is not available
    class RiskConfig:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
        def dict(self):
            return self.__dict__
    
    class Profile:
        CONSERVATIVE = "conservative"
        MODERATE = "moderate"
        AGGRESSIVE = "aggressive"
        ULTRA = "ultra"

# Configuration
SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Initialize FastAPI app with enhanced configuration
app = FastAPI(
    title="Enhanced Crypto Bot Control Plane",
    version="2.1.0",
    description="Advanced control interface for crypto trading bot with enhanced security and features",
    docs_url="/docs" if os.getenv('DEBUG') else None,  # Only show docs in debug mode
    redoc_url="/redoc" if os.getenv('DEBUG') else None
)

# CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup static files and templates
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND_DIR / "static"), name="static")
templates = Jinja2Templates(directory=FRONTEND_DIR / "templates")

# Enhanced WebSocket connection manager
class EnhancedConnectionManager:
    def __init__(self):
        self.active_connections: List[Dict[str, Any]] = []

    async def connect(self, websocket: WebSocket, client_id: str = None):
        await websocket.accept()
        connection_info = {
            "websocket": websocket,
            "client_id": client_id or secrets.token_urlsafe(8),
            "connected_at": datetime.utcnow(),
            "last_ping": datetime.utcnow()
        }
        self.active_connections.append(connection_info)
        logging.info(f"WebSocket client {connection_info['client_id']} connected")

    def disconnect(self, websocket: WebSocket):
        for connection in self.active_connections:
            if connection["websocket"] == websocket:
                self.active_connections.remove(connection)
                logging.info(f"WebSocket client {connection['client_id']} disconnected")
                break

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection["websocket"].send_text(json.dumps(message))
                connection["last_ping"] = datetime.utcnow()
            except Exception as e:
                logging.error(f"Failed to send message to client {connection['client_id']}: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.active_connections.remove(conn)

    async def send_to_client(self, client_id: str, message: dict):
        for connection in self.active_connections:
            if connection["client_id"] == client_id:
                try:
                    await connection["websocket"].send_text(json.dumps(message))
                    return True
                except Exception as e:
                    logging.error(f"Failed to send message to client {client_id}: {e}")
                    return False
        return False

    def get_connection_stats(self):
        return {
            "total_connections": len(self.active_connections),
            "connections": [
                {
                    "client_id": conn["client_id"],
                    "connected_at": conn["connected_at"].isoformat(),
                    "last_ping": conn["last_ping"].isoformat()
                }
                for conn in self.active_connections
            ]
        }

manager = EnhancedConnectionManager()

# Enhanced Data Models
class UserCredentials(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class RiskSettings(BaseModel):
    profile: str
    portfolio_risk: float
    max_position_size: float
    risk_per_trade: float
    max_daily_loss: float
    max_drawdown: float
    max_concurrent_positions: int
    consecutive_loss_kill: int

    @validator('portfolio_risk', 'max_position_size', 'risk_per_trade', 'max_daily_loss', 'max_drawdown')
    def validate_percentages(cls, v):
        if not 0 <= v <= 100:
            raise ValueError('Percentage values must be between 0 and 100')
        return v

    @validator('profile')
    def validate_profile(cls, v):
        valid_profiles = ['conservative', 'moderate', 'aggressive', 'ultra']
        if v not in valid_profiles:
            raise ValueError(f'Profile must be one of: {valid_profiles}')
        return v

class TradingSettings(BaseModel):
    min_volume_usd: float = 50_000.0
    max_spread_bps: float = 25.0
    top_n_symbols: int = 30
    tp_percent: float = 2.0
    sl_percent: float = 1.0
    trailing_stop_percent: float = 0.5
    strategy_weights: Dict[str, float] = {"momentum": 0.4, "mean_reversion": 0.3, "breakout": 0.3}

    @validator('strategy_weights')
    def validate_strategy_weights(cls, v):
        total = sum(v.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError('Strategy weights must sum to 1.0')
        return v

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
    bot_status: str = "running"
    connection_status: str = "connected"

class SystemHealth(BaseModel):
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    network_latency: float = 0.0
    last_error: Optional[str] = None
    error_count_24h: int = 0

# Authentication functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return username
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Global state with enhanced tracking
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
system_health = SystemHealth()

# Enhanced bot integration with multiple communication methods
class BotCommunicator:
    def __init__(self):
        self.communication_methods = ['file', 'redis', 'http']
        self.last_communication = None
        self.communication_errors = []

    async def apply_settings_to_bot(self, settings: dict) -> bool:
        """Enhanced bot communication with fallback methods"""
        success = False
        
        # Method 1: File-based communication (current method)
        try:
            bot_control_file = Path(__file__).parent.parent.parent / "bot_control.json"
            settings_with_timestamp = {
                **settings,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "control_ui"
            }
            
            with open(bot_control_file, 'w') as f:
                json.dump(settings_with_timestamp, f, indent=2, default=str)
            
            self.last_communication = datetime.utcnow()
            success = True
            logging.info("Settings applied to bot via file communication")
            
        except Exception as e:
            error_msg = f"File communication failed: {e}"
            logging.error(error_msg)
            self.communication_errors.append({
                "timestamp": datetime.utcnow(),
                "method": "file",
                "error": error_msg
            })

        # Method 2: Redis pub/sub (if available)
        try:
            import redis
            redis_client = redis.Redis(host='localhost', port=6379, db=0)
            redis_client.publish('bot_settings', json.dumps(settings, default=str))
            logging.info("Settings published to Redis")
            success = True
        except ImportError:
            logging.debug("Redis not available for bot communication")
        except Exception as e:
            logging.error(f"Redis communication failed: {e}")

        # Method 3: HTTP API call (if bot has HTTP endpoint)
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'http://localhost:8001/api/settings',
                    json=settings,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        logging.info("Settings applied via HTTP API")
                        success = True
        except ImportError:
            logging.debug("aiohttp not available for HTTP communication")
        except Exception as e:
            logging.error(f"HTTP communication failed: {e}")

        # Keep only last 10 errors
        if len(self.communication_errors) > 10:
            self.communication_errors = self.communication_errors[-10:]

        return success

    def get_communication_status(self):
        return {
            "last_communication": self.last_communication.isoformat() if self.last_communication else None,
            "recent_errors": self.communication_errors[-3:],  # Last 3 errors
            "error_count": len(self.communication_errors)
        }

bot_communicator = BotCommunicator()

# Authentication routes
@app.post("/api/auth/login", response_model=Token)
async def login(credentials: UserCredentials):
    """Enhanced login with proper authentication"""
    # In production, use proper user database
    # For now, using environment variables or defaults
    valid_username = os.getenv('ADMIN_USERNAME', 'admin')
    valid_password_hash = os.getenv('ADMIN_PASSWORD_HASH')
    
    if not valid_password_hash:
        # Default password is 'admin123' - change in production!
        valid_password_hash = get_password_hash('admin123')
    
    if credentials.username != valid_username or not verify_password(credentials.password, valid_password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": credentials.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

# Main routes
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Enhanced dashboard page"""
    return templates.TemplateResponse("enhanced_dashboard.html", {
        "request": request,
        "bot_name": "Ultra-Aggressive Crypto Bot",
        "version": "2.1.0"
    })

@app.get("/api/metrics")
async def get_metrics(username: str = Depends(verify_token)) -> BotMetrics:
    """Get current bot metrics with authentication"""
    return current_metrics

@app.get("/api/system-health")
async def get_system_health(username: str = Depends(verify_token)) -> SystemHealth:
    """Get system health metrics"""
    return system_health

@app.get("/api/connection-stats")
async def get_connection_stats(username: str = Depends(verify_token)):
    """Get WebSocket connection statistics"""
    return {
        "websocket_stats": manager.get_connection_stats(),
        "bot_communication": bot_communicator.get_communication_status()
    }

@app.get("/api/risk-settings")
async def get_risk_settings(username: str = Depends(verify_token)) -> RiskSettings:
    """Get current risk settings with authentication"""
    return current_risk_settings

@app.get("/api/trading-settings")
async def get_trading_settings(username: str = Depends(verify_token)) -> TradingSettings:
    """Get current trading settings with authentication"""
    return current_trading_settings

@app.post("/api/risk-settings")
async def update_risk_settings(settings: RiskSettings, username: str = Depends(verify_token)):
    """Update risk settings with enhanced validation and authentication"""
    try:
        # Enhanced validation using risk constraints
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
        
        # Send to bot with enhanced communication
        success = await bot_communicator.apply_settings_to_bot({
            "risk": current_risk_settings.dict(),
            "updated_by": username,
            "update_type": "risk_settings"
        })
        
        if success:
            # Broadcast to WebSocket clients
            await manager.broadcast({
                "type": "risk_settings_updated", 
                "data": current_risk_settings.dict(),
                "updated_by": username,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logging.info(f"Risk settings updated by {username}")
            return {
                "success": True, 
                "message": "Risk settings updated successfully",
                "settings": current_risk_settings.dict()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to apply settings to bot")
            
    except Exception as e:
        logging.error(f"Failed to update risk settings: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/trading-settings")
async def update_trading_settings(settings: TradingSettings, username: str = Depends(verify_token)):
    """Update trading settings with enhanced validation and authentication"""
    try:
        global current_trading_settings
        current_trading_settings = settings
        
        # Send to bot with enhanced communication
        success = await bot_communicator.apply_settings_to_bot({
            "trading": settings.dict(),
            "updated_by": username,
            "update_type": "trading_settings"
        })
        
        if success:
            await manager.broadcast({
                "type": "trading_settings_updated", 
                "data": settings.dict(),
                "updated_by": username,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logging.info(f"Trading settings updated by {username}")
            return {
                "success": True, 
                "message": "Trading settings updated successfully",
                "settings": settings.dict()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to apply settings to bot")
            
    except Exception as e:
        logging.error(f"Failed to update trading settings: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/emergency-stop")
async def emergency_stop(username: str = Depends(verify_token)):
    """Emergency stop with enhanced logging and authentication"""
    try:
        success = await bot_communicator.apply_settings_to_bot({
            "emergency_stop": True,
            "initiated_by": username,
            "timestamp": datetime.utcnow().isoformat(),
            "reason": "Manual emergency stop via control UI"
        })
        
        if success:
            await manager.broadcast({
                "type": "emergency_stop", 
                "data": {"initiated_by": username},
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logging.critical(f"Emergency stop activated by {username}")
            return {
                "success": True, 
                "message": "Emergency stop activated successfully",
                "initiated_by": username
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to stop bot")
            
    except Exception as e:
        logging.error(f"Emergency stop failed: {e}")
        raise HTTPException(status_code=500, detail=f"Emergency stop failed: {str(e)}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, client_id: str = None):
    """Enhanced WebSocket endpoint with client tracking"""
    await manager.connect(websocket, client_id)
    try:
        while True:
            # Send periodic updates
            await asyncio.sleep(2)
            
            # Send metrics update
            await websocket.send_text(json.dumps({
                "type": "metrics_update",
                "data": current_metrics.dict(),
                "timestamp": datetime.utcnow().isoformat()
            }))
            
            # Send system health update every 10 seconds
            if datetime.utcnow().second % 10 == 0:
                await websocket.send_text(json.dumps({
                    "type": "system_health_update",
                    "data": system_health.dict(),
                    "timestamp": datetime.utcnow().isoformat()
                }))
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Background tasks
async def update_metrics():
    """Enhanced background task to update metrics"""
    while True:
        await asyncio.sleep(5)
        
        try:
            # TODO: Fetch real metrics from bot
            global current_metrics, system_health
            
            # Update metrics timestamp
            current_metrics.last_updated = datetime.utcnow()
            current_metrics.uptime_hours += 5/3600  # Add 5 seconds
            
            # Simulate some metric variations for demo
            import random
            if current_metrics.portfolio_value == 0:
                current_metrics.portfolio_value = 15847.32
                current_metrics.realized_pnl_24h = 3247.18
                current_metrics.active_positions = 7
                current_metrics.win_rate = 0.742
                current_metrics.exposure_percent = 65.2
                current_metrics.heat_percent = 42.8
                current_metrics.sharpe_ratio = 2.34
                current_metrics.max_drawdown = 12.5
                current_metrics.rate_limit_remaining = 1150
                current_metrics.total_trades_24h = 23
            
            # Add small random variations
            current_metrics.portfolio_value += random.uniform(-50, 50)
            current_metrics.realized_pnl_24h += random.uniform(-10, 10)
            current_metrics.rate_limit_remaining = max(0, current_metrics.rate_limit_remaining + random.randint(-5, 5))
            
            # Update system health
            system_health.cpu_usage = random.uniform(10, 80)
            system_health.memory_usage = random.uniform(30, 70)
            system_health.disk_usage = random.uniform(20, 60)
            system_health.network_latency = random.uniform(10, 100)
            
            # Broadcast updates
            await manager.broadcast({
                "type": "metrics_update",
                "data": current_metrics.dict(),
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logging.error(f"Error updating metrics: {e}")
            system_health.last_error = str(e)
            system_health.error_count_24h += 1

@app.on_event("startup")
async def startup_event():
    """Enhanced startup with better logging and initialization"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logging.info("Starting Enhanced Crypto Bot Control Plane v2.1.0")
    logging.info(f"Frontend directory: {FRONTEND_DIR}")
    logging.info(f"Authentication enabled: {bool(os.getenv('ADMIN_PASSWORD_HASH'))}")
    
    # Start background tasks
    asyncio.create_task(update_metrics())
    
    logging.info("Enhanced Control Plane started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Graceful shutdown"""
    logging.info("Shutting down Enhanced Crypto Bot Control Plane")

if __name__ == "__main__":
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000, 
        reload=os.getenv('DEBUG', False),
        log_level="info"
    )

