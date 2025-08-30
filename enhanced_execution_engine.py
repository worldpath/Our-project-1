"""
Enhanced Execution Engine with TWAP and Iceberg Orders
=====================================================

Features:
- TWAP (Time-Weighted Average Price) execution
- Iceberg orders for large positions
- Smart order routing
- Slippage optimization
- Execution cost analysis
- Market impact modeling
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

class OrderType(Enum):
    """Enhanced order types"""
    MARKET = "market"
    LIMIT = "limit"
    TWAP = "twap"
    ICEBERG = "iceberg"
    ADAPTIVE = "adaptive"

class ExecutionStatus(Enum):
    """Order execution status"""
    PENDING = "pending"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"

@dataclass
class ExecutionMetrics:
    """Metrics for order execution analysis"""
    target_price: float = 0.0
    average_fill_price: float = 0.0
    total_slippage: float = 0.0
    total_fees: float = 0.0
    market_impact: float = 0.0
    execution_duration: float = 0.0
    fills: List[Dict] = field(default_factory=list)
    
    def calculate_slippage_bps(self) -> float:
        """Calculate slippage in basis points"""
        if self.target_price <= 0:
            return 0.0
        return abs(self.average_fill_price - self.target_price) / self.target_price * 10000
    
    def calculate_implementation_shortfall(self, benchmark_price: float) -> float:
        """Calculate implementation shortfall vs benchmark"""
        if benchmark_price <= 0:
            return 0.0
        return (self.average_fill_price - benchmark_price) / benchmark_price

@dataclass
class TWAPConfig:
    """TWAP execution configuration"""
    duration_minutes: int = 15
    slice_interval_seconds: int = 30
    min_slice_size: float = 0.01
    max_slice_size: float = 0.20
    participation_rate: float = 0.10  # 10% of volume
    price_limit_offset: float = 0.002  # 0.2% price limit
    
@dataclass
class IcebergConfig:
    """Iceberg order configuration"""
    visible_size: float = 0.1  # 10% of total size visible
    min_iceberg_size: float = 1000.0  # Minimum notional for iceberg
    refresh_interval: int = 5  # Refresh every 5 seconds
    price_improvement_threshold: float = 0.0005  # 0.05%

@dataclass
class EnhancedOrder:
    """Enhanced order with execution tracking"""
    order_id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    size: float
    order_type: OrderType
    target_price: Optional[float] = None
    
    # Execution parameters
    twap_config: Optional[TWAPConfig] = None
    iceberg_config: Optional[IcebergConfig] = None
    
    # State tracking
    status: ExecutionStatus = ExecutionStatus.PENDING
    filled_size: float = 0.0
    remaining_size: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    
    # Execution metrics
    metrics: ExecutionMetrics = field(default_factory=ExecutionMetrics)
    
    def __post_init__(self):
        self.remaining_size = self.size
        self.metrics.target_price = self.target_price or 0.0

class MarketDataProvider:
    """Interface for market data"""
    
    def get_current_price(self, symbol: str) -> float:
        """Get current market price"""
        raise NotImplementedError
    
    def get_orderbook(self, symbol: str, depth: int = 10) -> Dict:
        """Get orderbook data"""
        raise NotImplementedError
    
    def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get recent trade data"""
        raise NotImplementedError
    
    def get_volume_profile(self, symbol: str, period_minutes: int = 60) -> Dict:
        """Get volume profile data"""
        raise NotImplementedError

class ExchangeConnector:
    """Interface for exchange connectivity"""
    
    async def place_order(self, symbol: str, side: str, size: float, 
                         order_type: str = "market", price: float = None) -> Dict:
        """Place order on exchange"""
        raise NotImplementedError
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        raise NotImplementedError
    
    async def get_order_status(self, order_id: str) -> Dict:
        """Get order status"""
        raise NotImplementedError
    
    def get_trading_fees(self, symbol: str) -> Dict[str, float]:
        """Get trading fees (maker/taker)"""
        raise NotImplementedError

class VolumeAnalyzer:
    """Analyze volume patterns for execution optimization"""
    
    def __init__(self):
        self.volume_history = {}
    
    def analyze_volume_pattern(self, symbol: str, market_data: MarketDataProvider) -> Dict:
        """Analyze volume patterns to optimize execution"""
        try:
            volume_profile = market_data.get_volume_profile(symbol)
            recent_trades = market_data.get_recent_trades(symbol)
            
            # Calculate average volume per minute
            if recent_trades:
                volumes = [trade.get('volume', 0) for trade in recent_trades[-60:]]
                avg_volume_per_minute = np.mean(volumes) if volumes else 0
                volume_volatility = np.std(volumes) if len(volumes) > 1 else 0
            else:
                avg_volume_per_minute = 0
                volume_volatility = 0
            
            # Calculate participation rate recommendations
            safe_participation = 0.05  # Conservative 5%
            normal_participation = 0.10  # Normal 10%
            aggressive_participation = 0.20  # Aggressive 20%
            
            if volume_volatility > avg_volume_per_minute * 0.5:
                recommended_participation = safe_participation
                execution_speed = "slow"
            elif volume_volatility < avg_volume_per_minute * 0.2:
                recommended_participation = aggressive_participation
                execution_speed = "fast"
            else:
                recommended_participation = normal_participation
                execution_speed = "normal"
            
            return {
                'avg_volume_per_minute': avg_volume_per_minute,
                'volume_volatility': volume_volatility,
                'recommended_participation': recommended_participation,
                'execution_speed': execution_speed,
                'volume_pattern': 'stable' if volume_volatility < avg_volume_per_minute * 0.3 else 'volatile'
            }
            
        except Exception as e:
            logger.error(f"Volume analysis failed: {e}")
            return {
                'avg_volume_per_minute': 0,
                'volume_volatility': 0,
                'recommended_participation': 0.10,
                'execution_speed': 'normal',
                'volume_pattern': 'unknown'
            }

class TWAPExecutor:
    """TWAP execution engine"""
    
    def __init__(self, market_data: MarketDataProvider, exchange: ExchangeConnector):
        self.market_data = market_data
        self.exchange = exchange
        self.volume_analyzer = VolumeAnalyzer()
    
    async def execute_twap(self, order: EnhancedOrder) -> EnhancedOrder:
        """Execute TWAP strategy"""
        logger.info(f"Starting TWAP execution for {order.symbol}: {order.size} units over {order.twap_config.duration_minutes}min")
        
        start_time = time.time()
        config = order.twap_config
        
        # Analyze volume patterns
        volume_analysis = self.volume_analyzer.analyze_volume_pattern(order.symbol, self.market_data)
        
        # Adjust participation rate based on volume analysis
        adjusted_participation = min(
            config.participation_rate,
            volume_analysis['recommended_participation']
        )
        
        # Calculate slice parameters
        total_slices = (config.duration_minutes * 60) // config.slice_interval_seconds
        base_slice_size = order.remaining_size / total_slices
        
        slice_count = 0
        
        try:
            while order.remaining_size > 0 and slice_count < total_slices:
                # Calculate adaptive slice size
                current_volume = volume_analysis['avg_volume_per_minute'] * (config.slice_interval_seconds / 60)
                max_slice_by_volume = current_volume * adjusted_participation
                
                slice_size = min(
                    order.remaining_size,
                    max(config.min_slice_size, min(base_slice_size, max_slice_by_volume))
                )
                
                # Get current market data
                current_price = self.market_data.get_current_price(order.symbol)
                orderbook = self.market_data.get_orderbook(order.symbol)
                
                # Calculate limit price with offset
                if order.side == 'buy':
                    limit_price = current_price * (1 + config.price_limit_offset)
                    best_offer = orderbook.get('asks', [[current_price]])[0][0]
                    limit_price = min(limit_price, best_offer * 1.001)
                else:
                    limit_price = current_price * (1 - config.price_limit_offset)
                    best_bid = orderbook.get('bids', [[current_price]])[0][0]
                    limit_price = max(limit_price, best_bid * 0.999)
                
                # Place slice order
                try:
                    slice_result = await self.exchange.place_order(
                        symbol=order.symbol,
                        side=order.side,
                        size=slice_size,
                        order_type="limit",
                        price=limit_price
                    )
                    
                    if slice_result.get('status') == 'filled':
                        fill_price = slice_result.get('average_price', limit_price)
                        fill_size = slice_result.get('filled_size', slice_size)
                        fill_fees = slice_result.get('fees', 0)
                        
                        # Update order state
                        order.filled_size += fill_size
                        order.remaining_size -= fill_size
                        
                        # Update metrics
                        order.metrics.fills.append({
                            'timestamp': datetime.now(),
                            'price': fill_price,
                            'size': fill_size,
                            'fees': fill_fees
                        })
                        
                        logger.info(f"TWAP slice filled: {fill_size:.6f} @ {fill_price:.4f}")
                    
                except Exception as e:
                    logger.error(f"TWAP slice execution failed: {e}")
                
                slice_count += 1
                
                # Wait for next slice (unless last slice)
                if order.remaining_size > 0 and slice_count < total_slices:
                    await asyncio.sleep(config.slice_interval_seconds)
            
            # Calculate final metrics
            if order.metrics.fills:
                total_fill_value = sum(fill['price'] * fill['size'] for fill in order.metrics.fills)
                total_fill_size = sum(fill['size'] for fill in order.metrics.fills)
                
                if total_fill_size > 0:
                    order.metrics.average_fill_price = total_fill_value / total_fill_size
                    order.metrics.total_fees = sum(fill['fees'] for fill in order.metrics.fills)
                    order.metrics.total_slippage = abs(order.metrics.average_fill_price - order.metrics.target_price)
                
                order.status = ExecutionStatus.FILLED if order.remaining_size <= 0.001 else ExecutionStatus.PARTIALLY_FILLED
            
            order.metrics.execution_duration = time.time() - start_time
            
            logger.info(f"TWAP execution completed: {order.filled_size:.6f}/{order.size:.6f} filled, "
                       f"avg price: {order.metrics.average_fill_price:.4f}, "
                       f"slippage: {order.metrics.calculate_slippage_bps():.1f} bps")
            
        except Exception as e:
            logger.error(f"TWAP execution failed: {e}")
            order.status = ExecutionStatus.FAILED
        
        return order

class IcebergExecutor:
    """Iceberg order execution engine"""
    
    def __init__(self, market_data: MarketDataProvider, exchange: ExchangeConnector):
        self.market_data = market_data
        self.exchange = exchange
    
    async def execute_iceberg(self, order: EnhancedOrder) -> EnhancedOrder:
        """Execute Iceberg strategy"""
        logger.info(f"Starting Iceberg execution for {order.symbol}: {order.size} units")
        
        start_time = time.time()
        config = order.iceberg_config
        
        # Calculate visible slice size
        visible_size = min(
            order.size * config.visible_size,
            order.remaining_size
        )
        
        active_order_id = None
        last_price_update = time.time()
        
        try:
            while order.remaining_size > visible_size * 0.1:  # Continue while significant size remains
                
                current_slice_size = min(visible_size, order.remaining_size)
                
                # Get current market price
                current_price = self.market_data.get_current_price(order.symbol)
                
                # Determine order price (slightly aggressive to get fills)
                if order.side == 'buy':
                    order_price = current_price * 1.0005  # Slightly above market
                else:
                    order_price = current_price * 0.9995  # Slightly below market
                
                # Cancel existing order if price has moved significantly
                if active_order_id and (time.time() - last_price_update) > config.refresh_interval:
                    try:
                        await self.exchange.cancel_order(active_order_id)
                        active_order_id = None
                    except Exception as e:
                        logger.warning(f"Failed to cancel iceberg slice: {e}")
                
                # Place new slice if needed
                if not active_order_id:
                    try:
                        slice_result = await self.exchange.place_order(
                            symbol=order.symbol,
                            side=order.side,
                            size=current_slice_size,
                            order_type="limit",
                            price=order_price
                        )
                        
                        active_order_id = slice_result.get('order_id')
                        last_price_update = time.time()
                        
                        logger.info(f"Iceberg slice placed: {current_slice_size:.6f} @ {order_price:.4f}")
                        
                    except Exception as e:
                        logger.error(f"Failed to place iceberg slice: {e}")
                        break
                
                # Check for fills
                if active_order_id:
                    try:
                        order_status = await self.exchange.get_order_status(active_order_id)
                        
                        if order_status.get('status') in ['filled', 'partially_filled']:
                            filled_size = order_status.get('filled_size', 0)
                            avg_price = order_status.get('average_price', order_price)
                            fees = order_status.get('fees', 0)
                            
                            if filled_size > 0:
                                order.filled_size += filled_size
                                order.remaining_size -= filled_size
                                
                                # Record fill
                                order.metrics.fills.append({
                                    'timestamp': datetime.now(),
                                    'price': avg_price,
                                    'size': filled_size,
                                    'fees': fees
                                })
                                
                                logger.info(f"Iceberg slice filled: {filled_size:.6f} @ {avg_price:.4f}")
                        
                        if order_status.get('status') == 'filled':
                            active_order_id = None
                            
                    except Exception as e:
                        logger.error(f"Failed to check iceberg order status: {e}")
                
                # Brief pause before next iteration
                await asyncio.sleep(1)
            
            # Cancel any remaining order
            if active_order_id:
                try:
                    await self.exchange.cancel_order(active_order_id)
                except Exception as e:
                    logger.warning(f"Failed to cancel final iceberg order: {e}")
            
            # Calculate final metrics
            if order.metrics.fills:
                total_fill_value = sum(fill['price'] * fill['size'] for fill in order.metrics.fills)
                total_fill_size = sum(fill['size'] for fill in order.metrics.fills)
                
                if total_fill_size > 0:
                    order.metrics.average_fill_price = total_fill_value / total_fill_size
                    order.metrics.total_fees = sum(fill['fees'] for fill in order.metrics.fills)
                    order.metrics.total_slippage = abs(order.metrics.average_fill_price - order.metrics.target_price)
                
                order.status = ExecutionStatus.FILLED if order.remaining_size <= 0.001 else ExecutionStatus.PARTIALLY_FILLED
            
            order.metrics.execution_duration = time.time() - start_time
            
            logger.info(f"Iceberg execution completed: {order.filled_size:.6f}/{order.size:.6f} filled")
            
        except Exception as e:
            logger.error(f"Iceberg execution failed: {e}")
            order.status = ExecutionStatus.FAILED
        
        return order

class EnhancedExecutionEngine:
    """Main execution engine coordinating all order types"""
    
    def __init__(self, market_data: MarketDataProvider, exchange: ExchangeConnector):
        self.market_data = market_data
        self.exchange = exchange
        self.twap_executor = TWAPExecutor(market_data, exchange)
        self.iceberg_executor = IcebergExecutor(market_data, exchange)
        
        # Execution tracking
        self.active_orders: Dict[str, EnhancedOrder] = {}
        self.completed_orders: List[EnhancedOrder] = []
    
    def determine_optimal_execution(self, symbol: str, size: float, 
                                  daily_volume: float = None) -> OrderType:
        """Determine optimal execution strategy based on order size and market conditions"""
        
        try:
            # Get current price for notional calculation
            current_price = self.market_data.get_current_price(symbol)
            notional_value = size * current_price
            
            # Get volume analysis
            volume_analyzer = VolumeAnalyzer()
            volume_analysis = volume_analyzer.analyze_volume_pattern(symbol, self.market_data)
            
            # Decision logic
            if daily_volume and daily_volume > 0:
                size_ratio = size / daily_volume
                
                # Large orders (>10% of daily volume) use TWAP
                if size_ratio > 0.10:
                    return OrderType.TWAP
                
                # Medium orders (1-10% of daily volume) in volatile markets use Iceberg
                elif size_ratio > 0.01 and volume_analysis['volume_pattern'] == 'volatile':
                    return OrderType.ICEBERG
            
            # High notional value orders (>$10k) use smart execution
            if notional_value > 10000:
                if volume_analysis['execution_speed'] == 'slow':
                    return OrderType.TWAP
                else:
                    return OrderType.ICEBERG
            
            # Default to market orders for smaller sizes
            return OrderType.MARKET
            
        except Exception as e:
            logger.error(f"Error determining execution strategy: {e}")
            return OrderType.MARKET
    
    async def execute_order(self, order: EnhancedOrder) -> EnhancedOrder:
        """Execute order using appropriate strategy"""
        
        self.active_orders[order.order_id] = order
        
        try:
            if order.order_type == OrderType.TWAP:
                result = await self.twap_executor.execute_twap(order)
            elif order.order_type == OrderType.ICEBERG:
                result = await self.iceberg_executor.execute_iceberg(order)
            elif order.order_type == OrderType.MARKET:
                result = await self._execute_market_order(order)
            elif order.order_type == OrderType.LIMIT:
                result = await self._execute_limit_order(order)
            elif order.order_type == OrderType.ADAPTIVE:
                # Determine best strategy dynamically
                optimal_type = self.determine_optimal_execution(order.symbol, order.size)
                order.order_type = optimal_type
                result = await self.execute_order(order)  # Recursive call with determined type
            else:
                raise ValueError(f"Unsupported order type: {order.order_type}")
            
            # Move to completed orders
            if order.order_id in self.active_orders:
                del self.active_orders[order.order_id]
            self.completed_orders.append(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Order execution failed: {e}")
            order.status = ExecutionStatus.FAILED
            if order.order_id in self.active_orders:
                del self.active_orders[order.order_id]
            return order
    
    async def _execute_market_order(self, order: EnhancedOrder) -> EnhancedOrder:
        """Execute simple market order"""
        try:
            result = await self.exchange.place_order(
                symbol=order.symbol,
                side=order.side,
                size=order.size,
                order_type="market"
            )
            
            if result.get('status') == 'filled':
                order.filled_size = result.get('filled_size', order.size)
                order.remaining_size = order.size - order.filled_size
                order.status = ExecutionStatus.FILLED
                
                order.metrics.average_fill_price = result.get('average_price', 0)
                order.metrics.total_fees = result.get('fees', 0)
                order.metrics.fills.append({
                    'timestamp': datetime.now(),
                    'price': order.metrics.average_fill_price,
                    'size': order.filled_size,
                    'fees': order.metrics.total_fees
                })
            
            return order
            
        except Exception as e:
            logger.error(f"Market order execution failed: {e}")
            order.status = ExecutionStatus.FAILED
            return order
    
    async def _execute_limit_order(self, order: EnhancedOrder) -> EnhancedOrder:
        """Execute limit order"""
        try:
            result = await self.exchange.place_order(
                symbol=order.symbol,
                side=order.side,
                size=order.size,
                order_type="limit",
                price=order.target_price
            )
            
            order_id = result.get('order_id')
            
            # Wait for fill (simplified - in practice would be event-driven)
            max_wait_time = 300  # 5 minutes
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                order_status = await self.exchange.get_order_status(order_id)
                
                if order_status.get('status') == 'filled':
                    order.filled_size = order_status.get('filled_size', order.size)
                    order.remaining_size = order.size - order.filled_size
                    order.status = ExecutionStatus.FILLED
                    
                    order.metrics.average_fill_price = order_status.get('average_price', order.target_price)
                    order.metrics.total_fees = order_status.get('fees', 0)
                    break
                
                await asyncio.sleep(5)  # Check every 5 seconds
            
            return order
            
        except Exception as e:
            logger.error(f"Limit order execution failed: {e}")
            order.status = ExecutionStatus.FAILED
            return order
    
    def get_execution_statistics(self) -> Dict:
        """Get execution performance statistics"""
        if not self.completed_orders:
            return {}
        
        filled_orders = [o for o in self.completed_orders if o.status == ExecutionStatus.FILLED]
        
        if not filled_orders:
            return {}
        
        # Calculate aggregate statistics
        total_slippage_bps = [o.metrics.calculate_slippage_bps() for o in filled_orders]
        total_fees = [o.metrics.total_fees for o in filled_orders]
        execution_times = [o.metrics.execution_duration for o in filled_orders]
        
        return {
            'total_orders': len(self.completed_orders),
            'filled_orders': len(filled_orders),
            'fill_rate': len(filled_orders) / len(self.completed_orders),
            'average_slippage_bps': np.mean(total_slippage_bps) if total_slippage_bps else 0,
            'total_fees': sum(total_fees),
            'average_execution_time': np.mean(execution_times) if execution_times else 0,
            'order_types_used': {ot.value: sum(1 for o in filled_orders if o.order_type == ot) 
                               for ot in OrderType}
        }

# ============================================================================
# EXAMPLE USAGE
# ============================================================================

async def example_usage():
    """Example of how to use the enhanced execution engine"""
    
    # Mock implementations (replace with real exchange/data connections)
    class MockMarketData(MarketDataProvider):
        def get_current_price(self, symbol: str) -> float:
            return 50000.0  # Mock BTC price
        
        def get_orderbook(self, symbol: str, depth: int = 10) -> Dict:
            return {
                'bids': [[49995, 1.0], [49990, 2.0]],
                'asks': [[50005, 1.0], [50010, 2.0]]
            }
        
        def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
            return [{'volume': np.random.normal(0.5, 0.1)} for _ in range(limit)]
        
        def get_volume_profile(self, symbol: str, period_minutes: int = 60) -> Dict:
            return {'total_volume': 100.0}
    
    class MockExchange(ExchangeConnector):
        async def place_order(self, symbol: str, side: str, size: float, 
                             order_type: str = "market", price: float = None) -> Dict:
            return {
                'order_id': f"order_{int(time.time())}",
                'status': 'filled',
                'filled_size': size,
                'average_price': price or 50000.0,
                'fees': size * 50000.0 * 0.001
            }
        
        async def cancel_order(self, order_id: str) -> bool:
            return True
        
        async def get_order_status(self, order_id: str) -> Dict:
            return {'status': 'filled', 'filled_size': 1.0, 'average_price': 50000.0, 'fees': 50.0}
    
    # Initialize execution engine
    market_data = MockMarketData()
    exchange = MockExchange()
    execution_engine = EnhancedExecutionEngine(market_data, exchange)
    
    # Example 1: Large TWAP order
    twap_order = EnhancedOrder(
        order_id="twap_001",
        symbol="BTC/USDT",
        side="buy",
        size=2.0,
        order_type=OrderType.TWAP,
        target_price=50000.0,
        twap_config=TWAPConfig(
            duration_minutes=30,
            slice_interval_seconds=60,
            participation_rate=0.15
        )
    )
    
    result = await execution_engine.execute_order(twap_order)
    print(f"TWAP execution result: {result.status}, filled: {result.filled_size}")
    
    # Example 2: Iceberg order
    iceberg_order = EnhancedOrder(
        order_id="iceberg_001", 
        symbol="BTC/USDT",
        side="buy",
        size=5.0,
        order_type=OrderType.ICEBERG,
        target_price=49999.0,
        iceberg_config=IcebergConfig(visible_size=0.2)
    )
    
    result = await execution_engine.execute_order(iceberg_order)
    print(f"Iceberg execution result: {result.status}, filled: {result.filled_size}")
    
    # Print execution statistics
    stats = execution_engine.get_execution_statistics()
    print(f"Execution statistics: {stats}")

if __name__ == "__main__":
    asyncio.run(example_usage())