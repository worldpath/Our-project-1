
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    d = series.diff()
    up = d.clip(lower=0).rolling(period).mean()
    dn = (-d.clip(upper=0)).rolling(period).mean()
    rs = up / (dn.replace(0, np.nan))
    out = 100 - (100 / (1 + rs))
    return out.fillna(50.0)

def true_range(h, l, c):
    pc = c.shift(1)
    return pd.concat([h-l, (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1)

def atr(h, l, c, period=14):
    return true_range(h,l,c).rolling(period).mean()

def plus_dm(h,l):
    up = h.diff(); dn = -l.diff()
    return pd.Series(np.where((up>dn)&(up>0), up, 0.0), index=h.index)

def minus_dm(h,l):
    up = h.diff(); dn = -l.diff()
    return pd.Series(np.where((dn>up)&(dn>0), dn, 0.0), index=h.index)

def adx(h,l,c,period=14):
    trn = true_range(h,l,c).rolling(period).sum()
    pdmn = plus_dm(h,l).rolling(period).sum()
    mdmn = minus_dm(h,l).rolling(period).sum()
    pdi = 100*(pdmn / trn.replace(0,np.nan))
    mdi = 100*(mdmn / trn.replace(0,np.nan))
    dx = ((pdi-mdi).abs() / (pdi+mdi).replace(0,np.nan))*100
    return dx.rolling(period).mean().fillna(20.0)

def boll(series, period=20, std=2.0):
    ma = series.rolling(period).mean()
    sd = series.rolling(period).std(ddof=0)
    return ma - std*sd, ma, ma + std*sd

def donch(h,l,period=20):
    return l.rolling(period).min(), h.rolling(period).max()

@dataclass
class RegimeConfig:
    adx_trend_threshold: float = 22.0
    ema_long: int = 200
    ema_slope_lookback: int = 30
    crash_threshold: float = -0.06

def detect_regime(df: pd.DataFrame, cfg: RegimeConfig = RegimeConfig()) -> pd.Series:
    c,h,l = df["close"], df["high"], df["low"]
    ema_long = ema(c, cfg.ema_long)
    ax = adx(h,l,c,14)
    pct = ema_long.pct_change(cfg.ema_slope_lookback)
    reg = pd.Series(index=df.index, dtype="object")
    crash = pct <= cfg.crash_threshold
    uptrend = (pct>0) & (ax>=cfg.adx_trend_threshold)
    reg[crash] = "crash"; reg[uptrend] = "trend"; reg[reg.isna()] = "range"
    return reg

@dataclass
class Order:
    symbol: str; side: str; size: float; type: str
    price: Optional[float]=None; tag: Optional[str]=None

@dataclass
class ExitPlan:
    stop_price: float
    take_profit_prices: List[float] = field(default_factory=list)
    trail_atr_mult: float = 2.0
    time_exit_bars: int = 192

@dataclass
class Signal:
    timestamp: pd.Timestamp
    symbol: str
    entry: Order
    exit_plan: ExitPlan
    r_multiple: float

@dataclass
class StrategyParams:
    atr_period: int = 14
    stop_atr_mult: float = 2.5
    trail_atr_mult: float = 2.0
    partial_tp_r: float = 1.5
    tp2_r: float = 3.0
    time_exit_bars: int = 192
    boll_period: int = 20
    boll_std: float = 2.0
    rsi_period: int = 14
    adx_period: int = 14
    donchian_period: int = 20
    long_ema: int = 200
    mid_ema: int = 50
    fast_ema: int = 20

class BaseStrategy:
    def __init__(self, name: str, params: StrategyParams = StrategyParams()):
        self.name = name; self.p = params
    def _calc(self, df):
        c,h,l = df["close"], df["high"], df["low"]
        out = {"atr": atr(h,l,c,self.p.atr_period),
               "rsi": rsi(c,self.p.rsi_period),
               "adx": adx(h,l,c,self.p.adx_period),
               "ema200": ema(c,self.p.long_ema),
               "ema50": ema(c,self.p.mid_ema),
               "ema20": ema(c,self.p.fast_ema)}
        lb,mb,ub = boll(c, self.p.boll_period, self.p.boll_std)
        out["bb_lower"],out["bb_mid"],out["bb_upper"]=lb,mb,ub
        dlow,dup = donch(h,l,self.p.donchian_period)
        out["donch_lower"],out["donch_upper"]=dlow,dup
        return out
    def generate(self, df, symbol, regimes): raise NotImplementedError

class MomentumStrategy(BaseStrategy):
    def __init__(self, params=StrategyParams()): super().__init__("momentum", params)
    def generate(self, df, symbol, regimes):
        f = self._calc(df); sigs=[]
        for i in range(2,len(df)):
            if regimes.iloc[i]!="trend": continue
            c_i = df["close"].iloc[i]
            ema200_i, ema50_i, ema20_i = f["ema200"].iloc[i], f["ema50"].iloc[i], f["ema20"].iloc[i]
            adx_i, atr_i = f["adx"].iloc[i], f["atr"].iloc[i]
            if not (c_i>ema200_i and ema50_i>ema200_i and adx_i>=22): continue
            if not (df["close"].iloc[i-1] < ema20_i and c_i > ema20_i): continue
            stop = round(c_i - self.p.stop_atr_mult*atr_i, 8); 
            if stop<=0 or np.isnan(atr_i): continue
            R = c_i - stop
            tp1 = round(c_i + self.p.partial_tp_r*R, 8)
            tp2 = round(c_i + self.p.tp2_r*R, 8)
            sigs.append(Signal(df.index[i], symbol,
                               Order(symbol, "buy", 0.0, "limit", c_i, "momentum_entry"),
                               ExitPlan(stop, [tp1,tp2], self.p.trail_atr_mult, self.p.time_exit_bars),
                               R))
        return sigs

class MeanReversionStrategy(BaseStrategy):
    def __init__(self, params=StrategyParams()): super().__init__("mean_reversion", params)
    def generate(self, df, symbol, regimes):
        f = self._calc(df); sigs=[]
        for i in range(2,len(df)):
            if regimes.iloc[i]!="range": continue
            c_i = df["close"].iloc[i]; pc = df["close"].iloc[i-1]
            lb,mb,adx_i,rsi_i,atr_i = f["bb_lower"].iloc[i], f["bb_mid"].iloc[i], f["adx"].iloc[i], f["rsi"].iloc[i], f["atr"].iloc[i]
            if any(map(lambda x: np.isnan(x), [lb,mb,atr_i])): continue
            if not (adx_i<18 and rsi_i<35): continue
            if not (pc < f["bb_lower"].iloc[i-1] and c_i > lb): continue
            stop = round(c_i - self.p.stop_atr_mult*atr_i, 8); 
            if stop<=0: continue
            R = c_i - stop
            tp1 = float(min(mb, c_i + self.p.partial_tp_r*R))
            tp2 = round(c_i + self.p.tp2_r*R, 8)
            sigs.append(Signal(df.index[i], symbol,
                               Order(symbol,"buy",0.0,"limit",c_i,"mr_entry"),
                               ExitPlan(stop,[tp1,tp2], self.p.trail_atr_mult, self.p.time_exit_bars), R))
        return sigs

class BreakoutStrategy(BaseStrategy):
    def __init__(self, params=StrategyParams(), use_volume_filter=True):
        super().__init__("breakout", params); self.use_volume_filter=use_volume_filter
    def generate(self, df, symbol, regimes):
        f = self._calc(df); sigs=[]; vol_ma = df["volume"].rolling(20).mean() if "volume" in df.columns else None
        for i in range(2,len(df)):
            reg = regimes.iloc[i]
            if reg not in ("trend","range"): continue
            c_i = df["close"].iloc[i]; don_up=f["donch_upper"].iloc[i]; don_lo=f["donch_lower"].iloc[i]
            adx_i=f["adx"].iloc[i]; atr_i=f["atr"].iloc[i]
            if np.isnan(don_up) or np.isnan(atr_i): continue
            if adx_i<20: continue
            if not (c_i>don_up): continue
            if self.use_volume_filter and vol_ma is not None:
                if not (df["volume"].iloc[i] > 1.2 * vol_ma.iloc[i]): continue
            atr_stop = c_i - self.p.stop_atr_mult*atr_i
            stop = round(max(atr_stop, don_lo), 8); 
            if stop<=0: continue
            R = c_i - stop
            tp1 = round(c_i + self.p.partial_tp_r*R, 8)
            tp2 = round(c_i + self.p.tp2_r*R, 8)
            sigs.append(Signal(df.index[i], symbol,
                               Order(symbol,"buy",0.0,"limit",c_i,"breakout_entry"),
                               ExitPlan(stop,[tp1,tp2], self.p.trail_atr_mult, self.p.time_exit_bars), R))
        return sigs

def generate_signals_for_symbol(df: pd.DataFrame, symbol: str,
                                enabled=('momentum','mean_reversion','breakout'),
                                params: StrategyParams = StrategyParams(),
                                regime_cfg: RegimeConfig = RegimeConfig()) -> List[Signal]:
    reg = detect_regime(df, regime_cfg)
    sigs = []
    if 'momentum' in enabled: sigs += MomentumStrategy(params).generate(df, symbol, reg)
    if 'mean_reversion' in enabled: sigs += MeanReversionStrategy(params).generate(df, symbol, reg)
    if 'breakout' in enabled: sigs += BreakoutStrategy(params).generate(df, symbol, reg)
    return sigs
