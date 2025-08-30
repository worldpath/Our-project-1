"""
Enhanced Strategy Rules with Advanced Features
=============================================

Implements all recommended upgrades for aggressive crypto trading:
- Volatility breakout filters
- MACD confirmation signals  
- Short-selling capabilities
- Advanced regime detection with ML
- Chandelier exits
- Enhanced technical indicators
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Literal
import numpy as np
import pandas as pd
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# ENHANCED TECHNICAL INDICATORS
# ============================================================================

def ema(series: pd.Series, span: int) -> pd.Series:
    """Exponential Moving Average"""
    return series.ewm(span=span, adjust=False).mean()

def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average"""
    return series.rolling(period).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index"""
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi_vals = 100 - (100 / (1 + rs))
    return rsi_vals.fillna(50.0)

def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """MACD with Signal Line and Histogram"""
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def true_range(h: pd.Series, l: pd.Series, c: pd.Series) -> pd.Series:
    """True Range calculation"""
    pc = c.shift(1)
    tr1 = h - l
    tr2 = (h - pc).abs()
    tr3 = (l - pc).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

def atr(h: pd.Series, l: pd.Series, c: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range"""
    return true_range(h, l, c).rolling(period).mean()

def chandelier_exit(h: pd.Series, l: pd.Series, c: pd.Series, period: int = 22, multiplier: float = 3.0) -> Tuple[pd.Series, pd.Series]:
    """Chandelier Exit (ATR-based trailing stops)"""
    atr_vals = atr(h, l, c, period)
    
    # Long exit (below current price)
    highest_high = h.rolling(period).max()
    long_exit = highest_high - multiplier * atr_vals
    
    # Short exit (above current price)  
    lowest_low = l.rolling(period).min()
    short_exit = lowest_low + multiplier * atr_vals
    
    return long_exit, short_exit

def volatility_filter(h: pd.Series, l: pd.Series, c: pd.Series, period: int = 20, threshold: float = 1.5) -> pd.Series:
    """Volatility Breakout Filter - True when volatility exceeds threshold"""
    atr_vals = atr(h, l, c, period)
    atr_ma = atr_vals.rolling(period).mean()
    volatility_ratio = atr_vals / atr_ma
    return volatility_ratio > threshold

def adx_directional(h: pd.Series, l: pd.Series, c: pd.Series, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """ADX with DI+ and DI- components"""
    tr = true_range(h, l, c)
    
    # Directional Movement
    up_move = h.diff()
    down_move = -l.diff()
    
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=h.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=h.index)
    
    # Smoothed values
    tr_smooth = tr.rolling(period).sum()
    plus_dm_smooth = plus_dm.rolling(period).sum()
    minus_dm_smooth = minus_dm.rolling(period).sum()
    
    # Directional Indicators
    plus_di = 100 * (plus_dm_smooth / tr_smooth.replace(0, np.nan))
    minus_di = 100 * (minus_dm_smooth / tr_smooth.replace(0, np.nan))
    
    # ADX
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    adx_vals = dx.rolling(period).mean()
    
    return adx_vals.fillna(20.0), plus_di.fillna(0), minus_di.fillna(0)

def bollinger_bands(series: pd.Series, period: int = 20, std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Bollinger Bands"""
    ma = sma(series, period)
    sd = series.rolling(period).std(ddof=0)
    upper = ma + std * sd
    lower = ma - std * sd
    return lower, ma, upper

def donchian_channels(h: pd.Series, l: pd.Series, period: int = 20) -> Tuple[pd.Series, pd.Series]:
    """Donchian Channels"""
    upper = h.rolling(period).max()
    lower = l.rolling(period).min()
    return lower, upper

def vix_proxy(returns: pd.Series, window: int = 22) -> pd.Series:
    """VIX-like volatility proxy for crypto"""
    rolling_std = returns.rolling(window).std()
    return rolling_std * np.sqrt(365) * 100  # Annualized volatility percentage

# ============================================================================
# ENHANCED REGIME DETECTION WITH ML
# ============================================================================

@dataclass
class EnhancedRegimeConfig:
    """Enhanced regime detection configuration"""
    adx_trend_threshold: float = 22.0
    ema_long: int = 200
    ema_slope_lookback: int = 30
    crash_threshold: float = -0.06
    volatility_threshold: float = 1.5
    volume_threshold: float = 1.2
    use_ml_classification: bool = True
    ml_lookback: int = 100
    correlation_threshold: float = 0.7

def detect_enhanced_regime(df: pd.DataFrame, cfg: EnhancedRegimeConfig = EnhancedRegimeConfig()) -> pd.Series:
    """Enhanced regime detection with ML classification"""
    c, h, l, v = df["close"], df["high"], df["low"], df.get("volume", pd.Series(index=df.index))
    
    # Basic technical features
    ema_long = ema(c, cfg.ema_long)
    adx_vals, plus_di, minus_di = adx_directional(h, l, c, 14)
    atr_vals = atr(h, l, c, 14)
    rsi_vals = rsi(c, 14)
    
    # Volatility features
    returns = c.pct_change()
    volatility = volatility_filter(h, l, c)
    vix_like = vix_proxy(returns)
    
    # Trend features
    price_slope = ema_long.pct_change(cfg.ema_slope_lookback)
    
    # Volume features (if available)
    volume_ma = v.rolling(20).mean() if not v.empty else pd.Series(1.0, index=df.index)
    volume_ratio = (v / volume_ma).fillna(1.0) if not v.empty else pd.Series(1.0, index=df.index)
    
    if cfg.use_ml_classification and len(df) >= cfg.ml_lookback:
        return _ml_regime_classification(df, cfg, adx_vals, plus_di, minus_di, volatility, vix_like, price_slope, volume_ratio)
    else:
        return _rule_based_regime_detection(df, cfg, adx_vals, price_slope, volatility, vix_like)

def _rule_based_regime_detection(df: pd.DataFrame, cfg: EnhancedRegimeConfig, adx_vals: pd.Series, 
                                price_slope: pd.Series, volatility: pd.Series, vix_like: pd.Series) -> pd.Series:
    """Traditional rule-based regime detection"""
    regime = pd.Series(index=df.index, dtype="object")
    
    # Crash detection (enhanced)
    crash_condition = (price_slope <= cfg.crash_threshold) | (vix_like > vix_like.quantile(0.95))
    
    # Trend detection (enhanced)
    trend_condition = (
        (price_slope > 0) & 
        (adx_vals >= cfg.adx_trend_threshold) & 
        (volatility >= cfg.volatility_threshold)
    )
    
    # Range detection (default)
    regime[:] = "range"
    regime[crash_condition] = "crash"
    regime[trend_condition] = "trend"
    
    return regime

def _ml_regime_classification(df: pd.DataFrame, cfg: EnhancedRegimeConfig, adx_vals: pd.Series, 
                             plus_di: pd.Series, minus_di: pd.Series, volatility: pd.Series,
                             vix_like: pd.Series, price_slope: pd.Series, volume_ratio: pd.Series) -> pd.Series:
    """ML-based regime classification using KNN"""
    try:
        # Prepare features
        features = pd.DataFrame({
            'adx': adx_vals,
            'plus_di': plus_di,
            'minus_di': minus_di,
            'price_slope': price_slope,
            'volatility': volatility.astype(float),
            'vix_proxy': vix_like,
            'volume_ratio': volume_ratio,
            'rsi': rsi(df['close'], 14)
        }).fillna(method='forward').fillna(0)
        
        # Create labels based on enhanced rules
        crash_mask = (price_slope <= cfg.crash_threshold) | (vix_like > vix_like.quantile(0.95))
        trend_mask = (
            (price_slope > 0) & 
            (adx_vals >= cfg.adx_trend_threshold) & 
            (volatility >= cfg.volatility_threshold)
        )
        
        labels = pd.Series('range', index=df.index)
        labels[crash_mask] = 'crash'
        labels[trend_mask] = 'trend'
        
        # Train KNN classifier on recent data
        train_data = features.iloc[-cfg.ml_lookback:].dropna()
        train_labels = labels.iloc[-cfg.ml_lookback:][train_data.index]
        
        if len(train_data) < 20:  # Fallback to rules
            return labels
            
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(train_data)
        
        knn = KNeighborsClassifier(n_neighbors=5, weights='distance')
        knn.fit(X_scaled, train_labels)
        
        # Predict for all data
        all_data_scaled = scaler.transform(features.fillna(0))
        predictions = knn.predict(all_data_scaled)
        
        return pd.Series(predictions, index=df.index)
        
    except Exception:
        # Fallback to rule-based
        return _rule_based_regime_detection(df, cfg, adx_vals, price_slope, volatility, vix_like)

# ============================================================================
# ENHANCED ORDER AND SIGNAL CLASSES
# ============================================================================

@dataclass
class EnhancedOrder:
    """Enhanced order with short selling support"""
    symbol: str
    side: Literal["buy", "sell", "short", "cover"]  # Added short/cover
    size: float
    type: Literal["market", "limit", "twap", "iceberg"]  # Added TWAP/Iceberg
    price: Optional[float] = None
    tag: Optional[str] = None
    twap_duration: Optional[int] = None  # TWAP duration in minutes
    iceberg_size: Optional[float] = None  # Iceberg chunk size

@dataclass
class EnhancedExitPlan:
    """Enhanced exit plan with chandelier exits"""
    stop_price: float
    take_profit_prices: List[float] = field(default_factory=list)
    trail_atr_mult: float = 2.0
    time_exit_bars: int = 192
    
    # New chandelier exit parameters
    use_chandelier: bool = True
    chandelier_period: int = 22
    chandelier_mult: float = 3.0
    
    # Dynamic trailing parameters
    trail_tighten_after_tp1: bool = True
    trail_mult_reduction: float = 0.75

@dataclass
class EnhancedSignal:
    """Enhanced signal with risk metrics"""
    timestamp: pd.Timestamp
    symbol: str
    entry: EnhancedOrder
    exit_plan: EnhancedExitPlan
    r_multiple: float
    
    # New risk and performance metrics
    volatility_adjusted_r: float = 0.0
    correlation_risk: float = 0.0
    regime_confidence: float = 0.0
    expected_fees: float = 0.0

# ============================================================================
# ENHANCED STRATEGY PARAMETERS
# ============================================================================

@dataclass
class EnhancedStrategyParams:
    """Enhanced strategy parameters with all new features"""
    # Basic parameters
    atr_period: int = 14
    stop_atr_mult: float = 2.5
    trail_atr_mult: float = 2.0
    partial_tp_r: float = 1.5
    tp2_r: float = 3.0
    time_exit_bars: int = 192
    
    # Bollinger Bands
    boll_period: int = 20
    boll_std: float = 2.0
    
    # Oscillators
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    
    # Trend indicators
    adx_period: int = 14
    donchian_period: int = 20
    long_ema: int = 200
    mid_ema: int = 50
    fast_ema: int = 20
    
    # Enhanced features
    volatility_filter_period: int = 20
    volatility_threshold: float = 1.5
    use_macd_confirmation: bool = True
    use_volatility_filter: bool = True
    
    # Chandelier Exit
    chandelier_period: int = 22
    chandelier_mult: float = 3.0
    
    # Short selling
    enable_short_selling: bool = True
    short_rsi_threshold: float = 65
    
    # Position sizing with volatility adjustment
    use_volatility_position_sizing: bool = True
    volatility_scaling_factor: float = 2.0
    
    # Execution parameters
    use_twap_for_large_orders: bool = True
    large_order_threshold: float = 0.1  # 10% of daily volume
    twap_duration_minutes: int = 15
    
    # Risk parameters
    correlation_threshold: float = 0.7
    max_sector_exposure: float = 0.3

# ============================================================================
# BASE STRATEGY CLASS (ENHANCED)
# ============================================================================

class EnhancedBaseStrategy:
    """Enhanced base strategy with all new features"""
    
    def __init__(self, name: str, params: EnhancedStrategyParams = EnhancedStrategyParams()):
        self.name = name
        self.p = params
    
    def _calc_indicators(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate all technical indicators"""
        c, h, l = df["close"], df["high"], df["low"]
        v = df.get("volume", pd.Series(index=df.index))
        
        indicators = {
            # Basic indicators
            "atr": atr(h, l, c, self.p.atr_period),
            "rsi": rsi(c, self.p.rsi_period),
            "adx": adx_directional(h, l, c, self.p.adx_period)[0],
            "plus_di": adx_directional(h, l, c, self.p.adx_period)[1],
            "minus_di": adx_directional(h, l, c, self.p.adx_period)[2],
            
            # Moving averages
            "ema200": ema(c, self.p.long_ema),
            "ema50": ema(c, self.p.mid_ema),
            "ema20": ema(c, self.p.fast_ema),
            
            # MACD
            "macd": macd(c, self.p.macd_fast, self.p.macd_slow, self.p.macd_signal)[0],
            "macd_signal": macd(c, self.p.macd_fast, self.p.macd_slow, self.p.macd_signal)[1],
            "macd_histogram": macd(c, self.p.macd_fast, self.p.macd_slow, self.p.macd_signal)[2],
            
            # Volatility indicators
            "volatility_filter": volatility_filter(h, l, c, self.p.volatility_filter_period, self.p.volatility_threshold),
            "vix_proxy": vix_proxy(c.pct_change()),
            
            # Chandelier Exit
            "chandelier_long": chandelier_exit(h, l, c, self.p.chandelier_period, self.p.chandelier_mult)[0],
            "chandelier_short": chandelier_exit(h, l, c, self.p.chandelier_period, self.p.chandelier_mult)[1],
        }
        
        # Bollinger Bands
        bb_lower, bb_mid, bb_upper = bollinger_bands(c, self.p.boll_period, self.p.boll_std)
        indicators.update({
            "bb_lower": bb_lower,
            "bb_mid": bb_mid,
            "bb_upper": bb_upper
        })
        
        # Donchian Channels
        donch_lower, donch_upper = donchian_channels(h, l, self.p.donchian_period)
        indicators.update({
            "donch_lower": donch_lower,
            "donch_upper": donch_upper
        })
        
        return indicators
    
    def _calculate_volatility_adjusted_position_size(self, base_size: float, atr_val: float, price: float) -> float:
        """Calculate volatility-adjusted position size"""
        if not self.p.use_volatility_position_sizing:
            return base_size
            
        # ATR as percentage of price
        atr_pct = atr_val / price if price > 0 else 0
        
        # Adjust size inversely to volatility
        volatility_adjustment = 1.0 / (1.0 + atr_pct * self.p.volatility_scaling_factor)
        
        return base_size * volatility_adjustment
    
    def _should_use_twap(self, size: float, symbol: str, daily_volume: float = None) -> bool:
        """Determine if TWAP execution should be used"""
        if not self.p.use_twap_for_large_orders:
            return False
            
        if daily_volume and daily_volume > 0:
            size_ratio = size / daily_volume
            return size_ratio > self.p.large_order_threshold
            
        return False  # Conservative default
    
    def generate(self, df: pd.DataFrame, symbol: str, regimes: pd.Series) -> List[EnhancedSignal]:
        """Generate signals - to be implemented by subclasses"""
        raise NotImplementedError

# ============================================================================
# ENHANCED MOMENTUM STRATEGY
# ============================================================================

class EnhancedMomentumStrategy(EnhancedBaseStrategy):
    """Enhanced Momentum Strategy with volatility breakout filter"""
    
    def __init__(self, params: EnhancedStrategyParams = EnhancedStrategyParams()):
        super().__init__("enhanced_momentum", params)
    
    def generate(self, df: pd.DataFrame, symbol: str, regimes: pd.Series) -> List[EnhancedSignal]:
        indicators = self._calc_indicators(df)
        signals = []
        
        for i in range(2, len(df)):
            if regimes.iloc[i] != "trend":
                continue
                
            c_i = df["close"].iloc[i]
            c_prev = df["close"].iloc[i-1]
            
            # Get indicator values
            ema200_i = indicators["ema200"].iloc[i]
            ema50_i = indicators["ema50"].iloc[i]
            ema20_i = indicators["ema20"].iloc[i]
            ema20_prev = indicators["ema20"].iloc[i-1]
            adx_i = indicators["adx"].iloc[i]
            atr_i = indicators["atr"].iloc[i]
            volatility_filter_i = indicators["volatility_filter"].iloc[i]
            
            # Skip if invalid data
            if any(pd.isna([ema200_i, ema50_i, ema20_i, adx_i, atr_i])):
                continue
            
            # Enhanced momentum conditions
            trend_alignment = c_i > ema200_i and ema50_i > ema200_i
            momentum_breakout = c_prev <= ema20_prev and c_i > ema20_i
            strong_trend = adx_i >= 22
            
            # NEW: Volatility breakout filter
            volatility_confirmed = volatility_filter_i if self.p.use_volatility_filter else True
            
            if not (trend_alignment and momentum_breakout and strong_trend and volatility_confirmed):
                continue
            
            # Calculate stops and targets
            stop_price = round(c_i - self.p.stop_atr_mult * atr_i, 8)
            if stop_price <= 0:
                continue
                
            R = c_i - stop_price
            tp1 = round(c_i + self.p.partial_tp_r * R, 8)
            tp2 = round(c_i + self.p.tp2_r * R, 8)
            
            # Enhanced order with TWAP consideration
            order_type = "twap" if self._should_use_twap(0, symbol) else "market"
            twap_duration = self.p.twap_duration_minutes if order_type == "twap" else None
            
            entry_order = EnhancedOrder(
                symbol=symbol, 
                side="buy", 
                size=0.0,  # Will be calculated by risk manager
                type=order_type, 
                price=c_i, 
                tag="enhanced_momentum_entry",
                twap_duration=twap_duration
            )
            
            exit_plan = EnhancedExitPlan(
                stop_price=stop_price,
                take_profit_prices=[tp1, tp2],
                trail_atr_mult=self.p.trail_atr_mult,
                time_exit_bars=self.p.time_exit_bars,
                use_chandelier=True,
                chandelier_period=self.p.chandelier_period,
                chandelier_mult=self.p.chandelier_mult
            )
            
            signal = EnhancedSignal(
                timestamp=df.index[i],
                symbol=symbol,
                entry=entry_order,
                exit_plan=exit_plan,
                r_multiple=R,
                volatility_adjusted_r=R / atr_i if atr_i > 0 else R,
                regime_confidence=0.8 if volatility_confirmed else 0.6
            )
            
            signals.append(signal)
        
        return signals

# ============================================================================
# ENHANCED MEAN REVERSION STRATEGY  
# ============================================================================

class EnhancedMeanReversionStrategy(EnhancedBaseStrategy):
    """Enhanced Mean Reversion with MACD confirmation"""
    
    def __init__(self, params: EnhancedStrategyParams = EnhancedStrategyParams()):
        super().__init__("enhanced_mean_reversion", params)
    
    def generate(self, df: pd.DataFrame, symbol: str, regimes: pd.Series) -> List[EnhancedSignal]:
        indicators = self._calc_indicators(df)
        signals = []
        
        for i in range(2, len(df)):
            if regimes.iloc[i] != "range":
                continue
                
            c_i = df["close"].iloc[i]
            c_prev = df["close"].iloc[i-1]
            
            # Get indicator values
            bb_lower_i = indicators["bb_lower"].iloc[i]
            bb_lower_prev = indicators["bb_lower"].iloc[i-1]
            bb_mid_i = indicators["bb_mid"].iloc[i]
            adx_i = indicators["adx"].iloc[i]
            rsi_i = indicators["rsi"].iloc[i]
            atr_i = indicators["atr"].iloc[i]
            
            # MACD values for confirmation
            macd_i = indicators["macd"].iloc[i]
            macd_signal_i = indicators["macd_signal"].iloc[i]
            macd_prev = indicators["macd"].iloc[i-1]
            macd_signal_prev = indicators["macd_signal"].iloc[i-1]
            
            # Skip if invalid data
            if any(pd.isna([bb_lower_i, bb_mid_i, adx_i, rsi_i, atr_i, macd_i, macd_signal_i])):
                continue
            
            # Mean reversion conditions
            oversold_bounce = c_prev < bb_lower_prev and c_i > bb_lower_i
            low_trend_strength = adx_i < 18
            oversold_rsi = rsi_i < 35
            
            # NEW: MACD bullish divergence confirmation
            macd_confirmation = True
            if self.p.use_macd_confirmation:
                macd_bullish_cross = (macd_prev <= macd_signal_prev and macd_i > macd_signal_i)
                macd_confirmation = macd_bullish_cross or macd_i > macd_signal_i
            
            if not (oversold_bounce and low_trend_strength and oversold_rsi and macd_confirmation):
                continue
            
            # Calculate stops and targets
            stop_price = round(c_i - self.p.stop_atr_mult * atr_i, 8)
            if stop_price <= 0:
                continue
                
            R = c_i - stop_price
            tp1 = float(min(bb_mid_i, c_i + self.p.partial_tp_r * R))
            tp2 = round(c_i + self.p.tp2_r * R, 8)
            
            entry_order = EnhancedOrder(
                symbol=symbol, 
                side="buy", 
                size=0.0, 
                type="market", 
                price=c_i, 
                tag="enhanced_mr_entry"
            )
            
            exit_plan = EnhancedExitPlan(
                stop_price=stop_price,
                take_profit_prices=[tp1, tp2],
                trail_atr_mult=self.p.trail_atr_mult,
                time_exit_bars=self.p.time_exit_bars,
                use_chandelier=True,
                chandelier_period=self.p.chandelier_period,
                chandelier_mult=self.p.chandelier_mult
            )
            
            signal = EnhancedSignal(
                timestamp=df.index[i],
                symbol=symbol,
                entry=entry_order,
                exit_plan=exit_plan,
                r_multiple=R,
                volatility_adjusted_r=R / atr_i if atr_i > 0 else R,
                regime_confidence=0.9 if macd_confirmation else 0.5
            )
            
            signals.append(signal)
        
        return signals

# ============================================================================
# ENHANCED BREAKOUT STRATEGY WITH SHORT SELLING
# ============================================================================

class EnhancedBreakoutStrategy(EnhancedBaseStrategy):
    """Enhanced Breakout Strategy with short-selling for downtrends"""
    
    def __init__(self, params: EnhancedStrategyParams = EnhancedStrategyParams(), use_volume_filter: bool = True):
        super().__init__("enhanced_breakout", params)
        self.use_volume_filter = use_volume_filter
    
    def generate(self, df: pd.DataFrame, symbol: str, regimes: pd.Series) -> List[EnhancedSignal]:
        indicators = self._calc_indicators(df)
        signals = []
        
        # Volume analysis
        volume_ma = df["volume"].rolling(20).mean() if "volume" in df.columns else None
        
        for i in range(2, len(df)):
            if regimes.iloc[i] not in ("trend", "range"):
                continue
                
            c_i = df["close"].iloc[i]
            h_i = df["high"].iloc[i]
            l_i = df["low"].iloc[i]
            
            # Get indicator values
            donch_upper_i = indicators["donch_upper"].iloc[i]
            donch_lower_i = indicators["donch_lower"].iloc[i]
            adx_i = indicators["adx"].iloc[i]
            plus_di_i = indicators["plus_di"].iloc[i]
            minus_di_i = indicators["minus_di"].iloc[i]
            atr_i = indicators["atr"].iloc[i]
            rsi_i = indicators["rsi"].iloc[i]
            
            # Skip if invalid data
            if any(pd.isna([donch_upper_i, donch_lower_i, adx_i, atr_i])):
                continue
            
            # Volume confirmation
            volume_confirmed = True
            if self.use_volume_filter and volume_ma is not None:
                current_volume = df["volume"].iloc[i]
                volume_confirmed = current_volume > 1.2 * volume_ma.iloc[i]
            
            # Strong trend required
            if adx_i < 20:
                continue
            
            # LONG BREAKOUT (Original logic enhanced)
            if c_i > donch_upper_i and plus_di_i > minus_di_i and volume_confirmed:
                stop_price = max(c_i - self.p.stop_atr_mult * atr_i, donch_lower_i)
                stop_price = round(stop_price, 8)
                
                if stop_price <= 0 or stop_price >= c_i:
                    continue
                
                R = c_i - stop_price
                tp1 = round(c_i + self.p.partial_tp_r * R, 8)
                tp2 = round(c_i + self.p.tp2_r * R, 8)
                
                entry_order = EnhancedOrder(
                    symbol=symbol, 
                    side="buy", 
                    size=0.0, 
                    type="market", 
                    price=c_i, 
                    tag="enhanced_breakout_long"
                )
                
                exit_plan = EnhancedExitPlan(
                    stop_price=stop_price,
                    take_profit_prices=[tp1, tp2],
                    trail_atr_mult=self.p.trail_atr_mult,
                    time_exit_bars=self.p.time_exit_bars
                )
                
                signal = EnhancedSignal(
                    timestamp=df.index[i],
                    symbol=symbol,
                    entry=entry_order,
                    exit_plan=exit_plan,
                    r_multiple=R
                )
                
                signals.append(signal)
            
            # NEW: SHORT BREAKOUT for downtrends
            elif (self.p.enable_short_selling and 
                  c_i < donch_lower_i and 
                  minus_di_i > plus_di_i and 
                  rsi_i > self.p.short_rsi_threshold and 
                  volume_confirmed):
                
                stop_price = min(c_i + self.p.stop_atr_mult * atr_i, donch_upper_i)
                stop_price = round(stop_price, 8)
                
                if stop_price <= c_i:
                    continue
                
                R = stop_price - c_i  # Risk for short position
                tp1 = round(c_i - self.p.partial_tp_r * R, 8)
                tp2 = round(c_i - self.p.tp2_r * R, 8)
                
                entry_order = EnhancedOrder(
                    symbol=symbol, 
                    side="short", 
                    size=0.0, 
                    type="market", 
                    price=c_i, 
                    tag="enhanced_breakout_short"
                )
                
                exit_plan = EnhancedExitPlan(
                    stop_price=stop_price,
                    take_profit_prices=[tp1, tp2],
                    trail_atr_mult=self.p.trail_atr_mult,
                    time_exit_bars=self.p.time_exit_bars
                )
                
                signal = EnhancedSignal(
                    timestamp=df.index[i],
                    symbol=symbol,
                    entry=entry_order,
                    exit_plan=exit_plan,
                    r_multiple=R
                )
                
                signals.append(signal)
        
        return signals

# ============================================================================
# MAIN SIGNAL GENERATION FUNCTION
# ============================================================================

def generate_enhanced_signals(df: pd.DataFrame, symbol: str,
                            enabled: Tuple[str, ...] = ('enhanced_momentum', 'enhanced_mean_reversion', 'enhanced_breakout'),
                            params: EnhancedStrategyParams = EnhancedStrategyParams(),
                            regime_cfg: EnhancedRegimeConfig = EnhancedRegimeConfig()) -> List[EnhancedSignal]:
    """
    Generate enhanced signals with all new features
    
    Args:
        df: OHLCV data
        symbol: Trading pair symbol
        enabled: Enabled strategy names
        params: Strategy parameters
        regime_cfg: Regime detection configuration
    
    Returns:
        List of enhanced signals
    """
    # Detect market regime with enhanced ML features
    regimes = detect_enhanced_regime(df, regime_cfg)
    
    signals = []
    
    # Generate signals from enabled strategies
    if 'enhanced_momentum' in enabled:
        momentum_strategy = EnhancedMomentumStrategy(params)
        signals.extend(momentum_strategy.generate(df, symbol, regimes))
    
    if 'enhanced_mean_reversion' in enabled:
        mr_strategy = EnhancedMeanReversionStrategy(params)
        signals.extend(mr_strategy.generate(df, symbol, regimes))
    
    if 'enhanced_breakout' in enabled:
        breakout_strategy = EnhancedBreakoutStrategy(params, use_volume_filter=True)
        signals.extend(breakout_strategy.generate(df, symbol, regimes))
    
    return signals

# ============================================================================
# BACKWARD COMPATIBILITY WRAPPER
# ============================================================================

def generate_signals_for_symbol(df: pd.DataFrame, symbol: str,
                               enabled=('momentum','mean_reversion','breakout'),
                               params=None, regime_cfg=None) -> List:
    """Backward compatibility wrapper for existing code"""
    
    # Convert old parameter format to new format
    if params is None:
        enhanced_params = EnhancedStrategyParams()
    else:
        # Map old StrategyParams to EnhancedStrategyParams
        enhanced_params = EnhancedStrategyParams(
            atr_period=getattr(params, 'atr_period', 14),
            stop_atr_mult=getattr(params, 'stop_atr_mult', 2.5),
            trail_atr_mult=getattr(params, 'trail_atr_mult', 2.0),
            partial_tp_r=getattr(params, 'partial_tp_r', 1.5),
            tp2_r=getattr(params, 'tp2_r', 3.0),
            time_exit_bars=getattr(params, 'time_exit_bars', 192)
        )
    
    if regime_cfg is None:
        enhanced_regime_cfg = EnhancedRegimeConfig()
    else:
        # Map old RegimeConfig to EnhancedRegimeConfig  
        enhanced_regime_cfg = EnhancedRegimeConfig(
            adx_trend_threshold=getattr(regime_cfg, 'adx_trend_threshold', 22.0),
            ema_long=getattr(regime_cfg, 'ema_long', 200),
            ema_slope_lookback=getattr(regime_cfg, 'ema_slope_lookback', 30),
            crash_threshold=getattr(regime_cfg, 'crash_threshold', -0.06)
        )
    
    # Map old strategy names to enhanced names
    strategy_mapping = {
        'momentum': 'enhanced_momentum',
        'mean_reversion': 'enhanced_mean_reversion', 
        'breakout': 'enhanced_breakout'
    }
    
    enhanced_enabled = tuple(strategy_mapping.get(s, s) for s in enabled)
    
    # Generate enhanced signals
    enhanced_signals = generate_enhanced_signals(df, symbol, enhanced_enabled, enhanced_params, enhanced_regime_cfg)
    
    # Convert back to old Signal format for compatibility
    from strategy_rules import Signal, Order, ExitPlan
    
    compatible_signals = []
    for sig in enhanced_signals:
        old_signal = Signal(
            timestamp=sig.timestamp,
            symbol=sig.symbol,
            entry=Order(
                symbol=sig.entry.symbol,
                side=sig.entry.side if sig.entry.side in ['buy', 'sell'] else 'buy',  # Map short/cover to buy/sell
                size=sig.entry.size,
                type=sig.entry.type if sig.entry.type in ['market', 'limit'] else 'market',
                price=sig.entry.price,
                tag=sig.entry.tag
            ),
            exit_plan=ExitPlan(
                stop_price=sig.exit_plan.stop_price,
                take_profit_prices=sig.exit_plan.take_profit_prices,
                trail_atr_mult=sig.exit_plan.trail_atr_mult,
                time_exit_bars=sig.exit_plan.time_exit_bars
            ),
            r_multiple=sig.r_multiple
        )
        compatible_signals.append(old_signal)
    
    return compatible_signals