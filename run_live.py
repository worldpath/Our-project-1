
import os, time
from datetime import datetime, timedelta, timezone
from typing import Dict, List
import numpy as np, pandas as pd
import yaml

from strategy_rules import StrategyParams, RegimeConfig, generate_signals_for_symbol, Signal
from RiskManager import RiskManager
from correlation_utils import average_pairwise_corr
from exchange.binanceus_client import BinanceUSClient
from trade_logger import TradeLogger
from notifier import notify_email, notify_telegram

CONFIG_PATH = os.getenv("CONFIG_PATH","config/aggressive_production.yaml")
QUOTE = "USDT"; BAR_MIN = 15; LOOKBACK_BARS = 400

def round_to_step(x: float, step: float) -> float:
    return float(round(x/step)*step) if step>0 else float(x)

class PositionState:
    def __init__(self, symbol, size, entry, stop, tp1, tp2, trail_mult, time_exit_bars, opened_at, tag):
        self.symbol=symbol; self.size=float(size); self.entry=float(entry); self.stop=float(stop)
        self.tp1=float(tp1); self.tp2=float(tp2); self.trail_mult=float(trail_mult)
        self.time_exit_bars=int(time_exit_bars); self.opened_at=opened_at; self.tag=tag
        self.tp1_done=False; self.tp2_done=False

def load_config(p): 
    with open(p,"r") as f: return yaml.safe_load(f)

def align_to_next_15m():
    now = datetime.now(timezone.utc); mins=(now.minute//BAR_MIN)*BAR_MIN
    nxt = now.replace(minute=mins, second=0, microsecond=0)+timedelta(minutes=BAR_MIN)
    time.sleep(max(5,(nxt-now).total_seconds()+2))

def last_closed_bar(): 
    now = datetime.now(timezone.utc); mins=(now.minute//BAR_MIN)*BAR_MIN
    return now.replace(minute=mins, second=0, microsecond=0)

def _stub_true_range(df):
    pc=df["close"].shift(1)
    tr=pd.concat([(df["high"]-df["low"]), (df["high"]-pc).abs(), (df["low"]-pc).abs()], axis=1).max(axis=1)
    return tr
def _stub_adx(df, period=14):
    trn = _stub_true_range(df).rolling(period).sum()
    up = df["high"].diff(); dn = -df["low"].diff()
    pdm = ((up>dn)&(up>0))*up; mdm=((dn>up)&(dn>0))*dn
    pdmn=pdm.rolling(period).sum(); mdmn=mdm.rolling(period).sum()
    pdi=100*(pdmn/(trn.replace(0,np.nan))); mdi=100*(mdmn/(trn.replace(0,np.nan)))
    dx=((pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan))*100
    return dx.rolling(period).mean().fillna(20.0)

def main():
    cfg = load_config(CONFIG_PATH)
    symbols = cfg["execution"]["instruments"]
    risk_per_trade = float(cfg["risk"]["risk_per_trade"])
    routing = cfg.get("routing", {})
    per_strategy_risk = cfg.get("per_strategy_risk", {})
    lpo_cfg = cfg.get("limit_post_only", {})
    hybrid = cfg.get("hybrid_routing", {"enabled":True,"adx_threshold":25})
    strat_params = cfg.get("strategy_params", {"tp2_r":3.0})

    client = BinanceUSClient()
    logger = TradeLogger(cfg["reporting"]["trade_log_file"])
    rm = RiskManager(max_portfolio_heat=cfg["portfolio"]["max_portfolio_heat"],
                     max_daily_loss=cfg["portfolio"]["max_daily_loss"],
                     max_drawdown=cfg["portfolio"]["max_drawdown"],
                     max_concurrent=cfg["portfolio"]["concurrent_positions"],
                     correlation_gate=True, corr_threshold=0.60)
    rm.on_start()
    pos_states: Dict[str, PositionState] = {}

    print("[LIVE] Starting loop, waiting for next 15m close...")
    while True:
        align_to_next_15m()
        bar_ts = last_closed_bar()
        equity = client.get_equity(QUOTE)
        rm.on_bar_start(bar_ts, equity)
        ok, why = rm.can_trade()
        if not ok:
            print(f"[RISK] Blocked: {why}")
            try:
                if cfg.get("alerts",{}).get("enabled", False):
                    notify_email("[BOT] Risk Gate Blocked", f"{why} equity={equity:.2f}")
                    notify_telegram(f"[BOT] Risk Gate Blocked: {why} equity={equity:.2f}")
            except Exception: pass

        # Correlation
        price_dict = {}
        for s in symbols:
            df_tmp = client.fetch_ohlcv_15m(s, limit=min(200, LOOKBACK_BARS))
            price_dict[s] = df_tmp["close"]
        avg_corr = average_pairwise_corr(price_dict, window=96)

        # Manage exits
        for sym,p in list(pos_states.items()):
            px = client.fetch_ticker_price(sym)
            # time exit
            bars_open = int((bar_ts - p.opened_at).total_seconds() // (BAR_MIN*60))
            if bars_open >= p.time_exit_bars:
                order = client.place_market_sell(sym, p.size)
                logger.log(sym,"sell",p.size,px, order_id=str(order.get("id","")), tag=p.tag, note="time_exit")
                rm.register_exit(sym, (px - p.entry)*p.size, bar_ts)
                del pos_states[sym]; print(f"[EXIT] {sym} time exit"); continue
            # partials
            if (not p.tp1_done) and px >= p.tp1:
                qty = p.size/3.0
                order = client.place_market_sell(sym, qty)
                logger.log(sym,"sell",qty,px, order_id=str(order.get("id","")), tag=p.tag, note="partial_tp1")
                p.size -= qty; p.tp1_done=True; p.stop=max(p.stop,p.entry); rm.update_stop(sym,p.stop); rm.update_size(sym,p.size)
                print(f"[TP1] {sym} stop->{p.stop:.4f}")
            if p.tp1_done and (not p.tp2_done) and px >= p.tp2:
                qty = p.size/2.0
                order = client.place_market_sell(sym, qty)
                logger.log(sym,"sell",qty,px, order_id=str(order.get("id","")), tag=p.tag, note="partial_tp2")
                p.size -= qty; p.tp2_done=True; p.stop=max(p.stop,p.tp1); p.trail_mult=max(1.0, p.trail_mult*0.75)
                rm.update_stop(sym,p.stop); rm.update_size(sym,p.size)
                print(f"[TP2] {sym} stop->{p.stop:.4f} trail_mult={p.trail_mult:.2f}")
            # trailing
            recent = client.fetch_ohlcv_15m(sym, limit=20)
            tr = (recent["high"]-recent["low"]).mean()
            trail_stop = px - p.trail_mult * tr
            if trail_stop > p.stop:
                p.stop = trail_stop; rm.update_stop(sym,p.stop); print(f"[TRAIL] {sym} stop->{p.stop:.4f}")
            # hard stop
            if px <= p.stop:
                order = client.place_market_sell(sym, p.size)
                logger.log(sym,"sell",p.size,px, order_id=str(order.get("id","")), tag=p.tag, note="stop_hit")
                rm.register_exit(sym,(px-p.entry)*p.size,bar_ts); del pos_states[sym]; print(f"[STOP] {sym}"); continue

        # New entries
        if ok:
            params = StrategyParams(tp2_r=float(strat_params.get("tp2_r",3.0)))
            regime_cfg = RegimeConfig()
            for sym in symbols:
                if sym in pos_states: continue
                df = client.fetch_ohlcv_15m(sym, LOOKBACK_BARS)
                sigs: List[Signal] = generate_signals_for_symbol(df, sym, enabled=cfg["strategy"]["enabled_strategies"], params=params, regime_cfg=regime_cfg)
                if not sigs: continue
                sig = sigs[-1]
                sig_ts = sig.timestamp if sig.timestamp.tzinfo else sig.timestamp.tz_localize(timezone.utc)
                if sig_ts != df.index[-1]: continue

                entry, stop = float(sig.entry.price), float(sig.exit_plan.stop_price)
                tp1 = float(sig.exit_plan.take_profit_prices[0])
                tp2 = float(sig.exit_plan.take_profit_prices[1]) if len(sig.exit_plan.take_profit_prices)>1 else float(entry*1.02)
                trail = float(sig.exit_plan.trail_atr_mult); time_exit_bars=int(sig.exit_plan.time_exit_bars)

                strat_tag = sig.entry.tag.split('_')[0] if sig.entry.tag else 'momentum'
                use_risk = float(per_strategy_risk.get(strat_tag, risk_per_trade))
                lot_step = client.get_market_lot_step(sym)

                # Risk check
                assess = rm.assess_new_position(sym, entry, stop, equity, use_risk, lot_step=lot_step, avg_pairwise_corr=avg_corr)
                if not assess.accept:
                    print(f"[RISK] {sym} rejected: {assess.reason}")
                    continue

                # Size
                R = max(0.0, entry - stop)
                desired = 0.0 if R<=0 else (equity*use_risk)/R
                if lot_step>0: desired = (desired // lot_step) * lot_step
                size = min(desired, assess.max_size_units)
                if size<=0: continue

                # Routing
                use_order_type = routing.get(strat_tag, cfg["execution"].get("order_type","market"))
                # Hybrid override based on ADX
                if bool(hybrid.get("enabled",True)):
                    adx_series = _stub_adx(df,14); adx_val=float(adx_series.iloc[-1]) if len(adx_series) else 0.0
                    if adx_val >= float(hybrid.get("adx_threshold",25)):
                        use_order_type = "market"

                if use_order_type == "limit_post_only":
                    bid, ask = client.fetch_orderbook_top(sym)
                    price_step = client.get_price_step(sym)
                    price = round_to_step((bid or entry) - int(lpo_cfg.get("buy_offset_ticks",1))*price_step, price_step)
                    tries=0; maxr=int(lpo_cfg.get("max_retries",3))
                    while True:
                        try:
                            order = client.place_limit_maker_buy(sym, size, price); fill_px = price; break
                        except Exception:
                            tries+=1
                            if tries>maxr: raise
                            price = round_to_step(price - price_step, price_step); time.sleep(lpo_cfg.get("retry_sleep_ms",500)/1000.0)
                else:
                    order = client.place_market_buy(sym, size); fill_px = client.fetch_ticker_price(sym)

                opened_at = bar_ts
                rm.register_entry(sym, entry_price=fill_px, stop_price=stop, size_units=size, opened_at=opened_at, tag=sig.entry.tag)
                pos_states[sym] = PositionState(sym, size, fill_px, stop, tp1, tp2, trail, time_exit_bars, opened_at, sig.entry.tag)
                logger.log(sym,"buy",size,fill_px, order_id=str(order.get("id","")), tag=sig.entry.tag)
                print(f"[ENTRY] {sym} {strat_tag} size={size:.8f} @ {fill_px:.4f} stop={stop:.4f} tp1={tp1:.4f} tp2={tp2:.4f}")
                try:
                    if cfg.get("alerts",{}).get("enabled", False):
                        notify_email("[BOT] Entry", f"{sym} {strat_tag} size={size:.8f} @ {fill_px:.4f}")
                        notify_telegram(f"[BOT] Entry {sym} {strat_tag} size={size:.8f} @ {fill_px:.4f}")
                except Exception: pass

                # Try OCO
                try:
                    price_step = client.get_price_step(sym)
                    tp_price = round_to_step(tp1, price_step)
                    stop_lim = round_to_step(max(stop*0.999, stop - 2*price_step), price_step)
                    try:
                        client.place_oco_sell(sym, size/3.0, tp_price, stop_price=stop, stop_limit_price=stop_lim)
                        print(f"[EXIT ORDERS] {sym} OCO placed")
                    except Exception as e:
                        client.place_limit_sell(sym, size/3.0, tp_price)
                        client.place_stop_limit_sell(sym, size, stop_price=stop, limit_price=stop_lim)
                        print(f"[EXIT ORDERS] {sym} fallback TP+STOP used ({e})")
                except Exception as e:
                    print(f"[EXIT ORDERS] {sym} placement failed: {e}")

        rm.flush()
        time.sleep(1)

if __name__ == "__main__":
    main()
