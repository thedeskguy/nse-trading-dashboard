"""
Walk-forward signal backtester.

Strategies:
  indicator — generate_signal() composite technical score per bar (default)
  ml        — RandomForest next-day direction model, retrained every
              RETRAIN_EVERY bars on a walk-forward basis (see _ml_signals)

For each bar from warmup onward the strategy emits BUY/SELL/HOLD; the
simulator goes long on BUY, exits on SELL (long-only, close-price fills,
no transaction costs), and marks equity to market daily starting at 100.
Each equity point also carries a buy-&-hold benchmark normalised to 100
at the first signal bar.
"""
import numpy as np
import pandas as pd

WARMUP = 50         # bars before indicator signals are reliable (EMA-200 etc.)
ML_WARMUP = 120     # bars before the ML model has >= 60 clean training rows
RETRAIN_EVERY = 21  # ~1 trading month between RandomForest retrains

# ── v2 risk-management parameters ────────────────────────────────────────────
TREND_EMA = 200       # only enter long when close > EMA(200)
ATR_PERIOD = 14
SL_ATR_MULT = 2.0     # stop = entry − 2.0·ATR …
MAX_STOP_PCT = 0.10   # …but never risk more than 10% below entry (stop = the tighter of the two)
RR_RATIO = 3.0        # target = entry + RR_RATIO·risk  → 1:3 minimum reward:risk
RISK_PCT = 0.01       # risk 1% of equity to the stop per trade


def _atr(df: pd.DataFrame, period: int = ATR_PERIOD) -> np.ndarray:
    """Average True Range as a numpy array aligned to df (rolling SMA of TR)."""
    high = df["High"].astype(float).values
    low = df["Low"].astype(float).values
    close = df["Close"].astype(float).values
    prev_close = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum.reduce([
        high - low,
        np.abs(high - prev_close),
        np.abs(low - prev_close),
    ])
    return pd.Series(tr).rolling(period, min_periods=1).mean().values


def _ema(values: np.ndarray, period: int) -> np.ndarray:
    """Exponential moving average aligned to `values`."""
    return pd.Series(values, dtype=float).ewm(span=period, adjust=False).mean().values


def _simulate(dates, closes, atr, ema_trend, signals) -> dict:
    """Pure trade state machine over aligned per-bar arrays (all same length).

    Returns {"trades", "equity_curve", "open_position", "bars_long"}.
    Long-only, one position at a time, close-price fills. Equity starts at 100.
    """
    closes = np.asarray(closes, dtype=float)
    atr = np.asarray(atr, dtype=float)
    ema_trend = np.asarray(ema_trend, dtype=float)
    base_close = float(closes[0])

    trades: list[dict] = []
    equity_curve: list[dict] = []
    cash = 100.0
    invested = 0.0          # entry-time capital committed to the open position
    state = "flat"
    entry_date = ""
    entry_price = 0.0
    stop = target = init_risk = atr_entry = 0.0
    bars_long = 0

    for i, sig in enumerate(signals):
        close = float(closes[i])
        date = dates[i]

        # ── exit checks (while long) ─────────────────────────────────────────
        if state == "long":
            exit_reason = None
            if close <= stop:                 # fixed stop-loss (no trailing)
                exit_reason = "stop"
            elif close >= target:
                exit_reason = "target"
            elif sig == "SELL":
                exit_reason = "signal"

            if exit_reason:
                cash += invested * close / entry_price          # realise
                trades.append({
                    "date_entry":  entry_date,
                    "date_exit":   date,
                    "entry_price": round(entry_price, 2),
                    "exit_price":  round(close, 2),
                    "pnl_pct":     round((close - entry_price) / entry_price * 100, 2),
                    "exit_reason": exit_reason,
                    "r_multiple":  round((close - entry_price) / init_risk, 2)
                                   if init_risk else 0.0,
                })
                invested = 0.0
                state = "flat"

        # ── entry (flat + BUY + uptrend) ─────────────────────────────────────
        if state == "flat" and sig == "BUY" and close > float(ema_trend[i]):
            atr_entry = float(atr[i])
            if atr_entry > 0:
                # ATR-based stop, but never wider than MAX_STOP_PCT of entry.
                stop = close - min(SL_ATR_MULT * atr_entry, MAX_STOP_PCT * close)
                init_risk = close - stop
                target = close + RR_RATIO * init_risk
                stop_dist_pct = init_risk / close
                alloc = min(1.0, RISK_PCT / stop_dist_pct) if stop_dist_pct > 0 else 0.0
                equity = cash                                   # flat -> equity == cash
                invested = alloc * equity
                cash = equity - invested
                entry_price = close
                entry_date = date
                state = "long"

        # ── mark to market ───────────────────────────────────────────────────
        eq = cash + (invested * close / entry_price if state == "long" else 0.0)
        equity_curve.append({
            "date": date,
            "equity": round(eq, 2),
            "benchmark": round(100.0 * close / base_close, 2),
        })
        if state == "long":
            bars_long += 1

    # ── open position (not force-closed) ─────────────────────────────────────
    open_position = None
    if state == "long":
        last = float(closes[-1])
        open_position = {
            "date_entry":         entry_date,
            "entry_price":        round(entry_price, 2),
            "current_price":      round(last, 2),
            "unrealized_pnl_pct": round((last - entry_price) / entry_price * 100, 2),
            "days_held":          (
                pd.Timestamp(dates[-1]) - pd.Timestamp(entry_date)
            ).days,
            "stop":               round(stop, 2),
            "target":             round(target, 2),
            "exit_reason":        None,
        }

    return {
        "trades": trades,
        "equity_curve": equity_curve,
        "open_position": open_position,
        "bars_long": bars_long,
    }


STRATEGY_DESCRIPTIONS = {
    "indicator": (
        "Trades the composite technical indicator signal (RSI, MACD, EMA trend, "
        "Bollinger Bands, support/resistance, OBV). Long-only: BUY to enter, "
        "SELL to exit, close-price fills."
        " Entries require an uptrend (close > EMA-200); exits on a 2·ATR stop (capped at 10% below entry), a 1:3 ATR take-profit, or the strategy's SELL signal; positions are risk-sized to 1% of equity."
    ),
    "ml": (
        "Trades a RandomForest next-day direction model retrained every "
        f"{RETRAIN_EVERY} bars walk-forward. Enters when P(up) ≥ 55%, exits "
        "when P(up) ≤ 45%. Long-only, close-price fills."
        " Entries require an uptrend (close > EMA-200); exits on a 2·ATR stop (capped at 10% below entry), a 1:3 ATR take-profit, or the strategy's SELL signal; positions are risk-sized to 1% of equity."
    ),
}


def _empty_result(strategy: str, error: str | None = None) -> dict:
    return {
        "trades": [],
        "open_position": None,
        "equity_curve": [],
        "stats": _compute_stats([], [], 100.0, 0, 0, 0.0),
        "strategy": strategy,
        "strategy_description": STRATEGY_DESCRIPTIONS.get(strategy, f"Unknown strategy: {strategy}"),
        "error": error,
    }


def _indicator_signals(df: pd.DataFrame, warmup: int) -> list[str]:
    from tools.generate_signals import generate_signal

    signals: list[str] = []
    for i in range(warmup, len(df)):
        try:
            signals.append(generate_signal(df.iloc[: i + 1])["signal"])
        except Exception:
            signals.append("HOLD")
    return signals


def _ml_signals(df: pd.DataFrame, warmup: int) -> list[str]:
    from sklearn.ensemble import RandomForestClassifier

    from tools.ml_predictor import FEATURE_COLS, build_features

    feat = build_features(df)
    signals: list[str] = []
    model = None
    col_means = None

    for i in range(warmup, len(df)):
        if model is None or (i - warmup) % RETRAIN_EVERY == 0:
            # feat.iloc[:i] = rows 0..i-1. Row i-1's target (close[i] > close[i-1])
            # is known by the close of bar i, so this window has no look-ahead.
            train = feat.iloc[:i].dropna(subset=FEATURE_COLS + ["target"])
            if len(train) < 60:
                model = None
                signals.append("HOLD")
                continue
            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=6,
                min_samples_leaf=5,
                random_state=42,
                n_jobs=-1,
            )
            model.fit(train[FEATURE_COLS].values, train["target"].values.astype(int))
            col_means = train[FEATURE_COLS].mean().values

        row = feat.iloc[[i]][FEATURE_COLS].values.astype(float).copy()
        nan_mask = np.isnan(row[0])
        row[0][nan_mask] = col_means[nan_mask]

        classes = list(model.classes_)
        if len(classes) == 1:
            # One-class training window: the model can't estimate P(up), so
            # don't trade on it — emit HOLD until the next retrain.
            signals.append("HOLD")
            continue
        p_up = float(model.predict_proba(row)[0][classes.index(1)])

        if p_up >= 0.55:
            signals.append("BUY")
        elif p_up <= 0.45:
            signals.append("SELL")
        else:
            signals.append("HOLD")
    return signals


# ── strategy preset parameters ───────────────────────────────────────────────
TREND_FAST_EMA = 50
TREND_SLOW_EMA = 200
TREND_WARMUP = 200          # EMA-200 needs seasoning before the cross is meaningful


def _trend_signals(df: pd.DataFrame, warmup: int) -> list[str]:
    """Trend-following: BUY while EMA-50 > EMA-200, else SELL (enter golden cross)."""
    fast = df.get(f"EMA_{TREND_FAST_EMA}")
    slow = df.get(f"EMA_{TREND_SLOW_EMA}")
    signals: list[str] = []
    for i in range(warmup, len(df)):
        try:
            signals.append("BUY" if float(fast.iloc[i]) > float(slow.iloc[i]) else "SELL")
        except Exception:
            signals.append("HOLD")
    return signals


def _compute_stats(
    trades: list[dict],
    equity_curve: list[dict],
    final_equity: float,
    bars_long: int,
    n_signal_bars: int,
    buy_hold_return_pct: float,
) -> dict:
    num_trades = len(trades)
    wins = [t for t in trades if t["pnl_pct"] > 0]
    # Breakeven trades count as losses (win_rate is strict), matching the original engine.
    losses = [t for t in trades if t["pnl_pct"] <= 0]

    eq = np.array([p["equity"] for p in equity_curve], dtype=float)
    sharpe = 0.0
    if len(eq) >= 3 and not np.any(eq[:-1] == 0):
        rets = np.diff(eq) / eq[:-1]
        std = np.std(rets)
        if std > 0:
            sharpe = round(float(np.mean(rets) / std * np.sqrt(252)), 2)

    gross_gain = sum(t["pnl_pct"] for t in wins)
    gross_loss = abs(sum(t["pnl_pct"] for t in losses))
    profit_factor = round(gross_gain / gross_loss, 2) if gross_loss > 0 else None

    if trades:
        hold = [
            (pd.Timestamp(t["date_exit"]) - pd.Timestamp(t["date_entry"])).days
            for t in trades
        ]
        avg_hold_days = round(sum(hold) / len(hold), 1)
    else:
        avg_hold_days = 0.0

    # ── v2 richer metrics ────────────────────────────────────────────────────
    n = len(equity_curve)
    cagr = 0.0
    if n >= 2 and final_equity > 0:
        cagr = round(((final_equity / 100.0) ** (252.0 / n) - 1.0) * 100, 2)

    sortino = 0.0
    if len(eq) >= 3 and not np.any(eq[:-1] == 0):
        rets = np.diff(eq) / eq[:-1]
        downside = rets[rets < 0]
        dd_std = np.std(downside) if len(downside) else 0.0
        if dd_std > 0:
            sortino = round(float(np.mean(rets) / dd_std * np.sqrt(252)), 2)

    max_dd_v2 = _max_drawdown(equity_curve)
    calmar = round(cagr / abs(max_dd_v2), 2) if max_dd_v2 < 0 else None

    pnls = [t["pnl_pct"] for t in trades]
    best_trade = round(max(pnls), 2) if pnls else 0.0
    worst_trade = round(min(pnls), 2) if pnls else 0.0

    max_consec = run = 0
    for t in trades:
        if t["pnl_pct"] <= 0:
            run += 1
            max_consec = max(max_consec, run)
        else:
            run = 0

    return {
        "num_trades":         num_trades,
        "win_rate":           round(len(wins) / num_trades, 3) if num_trades else 0.0,
        "total_return_pct":   round(final_equity - 100.0, 2),
        "avg_gain_pct":       round(sum(t["pnl_pct"] for t in wins) / len(wins), 2) if wins else 0.0,
        "avg_loss_pct":       round(sum(t["pnl_pct"] for t in losses) / len(losses), 2) if losses else 0.0,
        "max_drawdown_pct":   _max_drawdown(equity_curve),
        "sharpe_ratio":       sharpe,
        "profit_factor":      profit_factor,
        "exposure_pct":       round(100.0 * bars_long / n_signal_bars, 1) if n_signal_bars else 0.0,
        "avg_hold_days":      avg_hold_days,
        "buy_hold_return_pct": round(buy_hold_return_pct, 2),
        "cagr_pct":               cagr,
        "sortino_ratio":          sortino,
        "calmar_ratio":           calmar,
        "best_trade_pct":         best_trade,
        "worst_trade_pct":        worst_trade,
        "max_consecutive_losses": max_consec,
    }


def _max_drawdown(equity_curve: list[dict]) -> float:
    peak = 100.0
    max_dd = 0.0
    for point in equity_curve:
        if point["equity"] > peak:
            peak = point["equity"]
        dd = (point["equity"] - peak) / peak * 100
        if dd < max_dd:
            max_dd = dd
    return round(max_dd, 2)


def run_backtest(df: pd.DataFrame, strategy: str = "indicator") -> dict:
    if strategy not in STRATEGY_DESCRIPTIONS:
        raise ValueError(f"Unknown strategy: {strategy!r}")

    warmup = ML_WARMUP if strategy == "ml" else WARMUP

    if strategy == "ml" and len(df) < ML_WARMUP + RETRAIN_EVERY:
        return _empty_result(
            strategy,
            error="Not enough history for an ML backtest — use a 1y or 2y period.",
        )
    if len(df) < warmup + 2:
        return _empty_result(strategy)

    closes = df["Close"].values
    if hasattr(df.index, "strftime"):
        dates = df.index.strftime("%Y-%m-%d").tolist()
    else:
        dates = [str(d)[:10] for d in df.index]

    signals = _ml_signals(df, warmup) if strategy == "ml" else _indicator_signals(df, warmup)

    atr_full = _atr(df, ATR_PERIOD)
    ema_full = _ema(df["Close"].astype(float).values, TREND_EMA)

    # Align arrays to the signal window (bars warmup … end).
    sim = _simulate(
        dates[warmup:], closes[warmup:], atr_full[warmup:], ema_full[warmup:], signals
    )

    base_close = float(closes[warmup])
    final_equity = sim["equity_curve"][-1]["equity"] if sim["equity_curve"] else 100.0
    buy_hold_return_pct = 100.0 * (float(closes[-1]) / base_close - 1.0)

    return {
        "trades": sim["trades"],
        "open_position": sim["open_position"],
        "equity_curve": sim["equity_curve"],
        "stats": _compute_stats(
            sim["trades"], sim["equity_curve"], final_equity,
            sim["bars_long"], len(signals), buy_hold_return_pct,
        ),
        "strategy": strategy,
        "strategy_description": STRATEGY_DESCRIPTIONS[strategy],
        "error": None,
    }
