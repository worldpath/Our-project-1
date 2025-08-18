# correlation_utils.py
import pandas as pd
import numpy as np
from typing import Dict, Optional

def average_pairwise_corr(price_dict: Dict[str, pd.Series], window: Optional[int] = None) -> float:
    """
    Compute the average pairwise correlation of log returns across symbols.
    price_dict: { "BTC/USDT": close_series, ... } with a DateTimeIndex
    window: optional lookback window for correlation (e.g., 96 bars)
    """
    if len(price_dict) < 2:
        return float("nan")

    rets = {}
    for sym, s in price_dict.items():
        if not isinstance(s, pd.Series):
            s = pd.Series(s)
        if window and len(s) >= window:
            s = s.iloc[-window:]
        # log returns; drop NaNs
        r = np.log(s).diff().dropna()
        if not r.empty:
            rets[sym] = r

    if len(rets) < 2:
        return float("nan")

    df = pd.DataFrame(rets).dropna(how="any")
    if df.shape[1] < 2:
        return float("nan")

    corr = df.corr()
    # take upper triangle without diagonal
    vals = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool)).stack().values
    return float(np.nanmean(vals)) if len(vals) else float("nan")
