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

STRATEGY_DESCRIPTIONS = {
    "indicator": (
        "Trades the composite technical indicator signal (RSI, MACD, EMA trend, "
        "Bollinger Bands, support/resistance, OBV). Long-only: BUY to enter, "
        "SELL to exit, close-price fills."
    ),
    "ml": (
        "Trades a RandomForest next-day direction model retrained every "
        f"{RETRAIN_EVERY} bars walk-forward. Enters when P(up) ≥ 55%, exits "
        "when P(up) ≤ 45%. Long-only, close-price fills."
    ),
}


def _empty_result(strategy: str, error: str | None = None) -> dict:
    return {
        "trades": [],
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

    # ── Trade simulation + daily MTM equity + benchmark (single pass) ────────
    base_close = float(closes[warmup])
    trades: list[dict] = []
    equity_curve: list[dict] = []
    committed_equity = 100.0
    state = "flat"
    entry_price = 0.0
    entry_date = ""
    bars_long = 0

    for i, sig in enumerate(signals):
        row_idx = warmup + i
        close = float(closes[row_idx])
        date = dates[row_idx]

        if state == "flat" and sig == "BUY":
            state = "long"
            entry_price = close
            entry_date = date
        elif state == "long" and sig == "SELL":
            committed_equity *= close / entry_price
            trades.append({
                "date_entry":  entry_date,
                "date_exit":   date,
                "entry_price": round(entry_price, 2),
                "exit_price":  round(close, 2),
                "pnl_pct":     round((close - entry_price) / entry_price * 100, 2),
            })
            state = "flat"

        if state == "long":
            bars_long += 1
            daily_eq = committed_equity * (close / entry_price)
        else:
            daily_eq = committed_equity

        equity_curve.append({
            "date": date,
            "equity": round(daily_eq, 2),
            "benchmark": round(100.0 * close / base_close, 2),
        })

    # Force-close any open position at the final bar
    if state == "long":
        close = float(closes[-1])
        committed_equity *= close / entry_price
        trades.append({
            "date_entry":  entry_date,
            "date_exit":   dates[-1],
            "entry_price": round(entry_price, 2),
            "exit_price":  round(close, 2),
            "pnl_pct":     round((close - entry_price) / entry_price * 100, 2),
        })

    buy_hold_return_pct = 100.0 * (float(closes[-1]) / base_close - 1.0)

    return {
        "trades": trades,
        "equity_curve": equity_curve,
        "stats": _compute_stats(
            trades, equity_curve, committed_equity,
            bars_long, len(signals), buy_hold_return_pct,
        ),
        "strategy": strategy,
        "strategy_description": STRATEGY_DESCRIPTIONS[strategy],
        "error": None,
    }
