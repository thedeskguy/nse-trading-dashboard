"""
Walk-forward signal backtester.

For each bar from WARMUP onward, generates a signal using generate_signal()
on the rolling window df.iloc[:i+1], then simulates BUY-on-signal / SELL-on-signal
trades using the day's Close price.

Returns a JSON-serialisable dict with:
  trades       — list of individual round-trip trades
  equity_curve — portfolio value over time (starts at 100)
  stats        — aggregate win rate, total return, drawdown, etc.
"""
import pandas as pd

WARMUP = 50  # rows before signals are reliable (enough data for EMA-200, etc.)


def run_backtest(df: pd.DataFrame) -> dict:
    if len(df) < WARMUP + 2:
        return {
            "trades": [],
            "equity_curve": [],
            "stats": {
                "num_trades": 0,
                "win_rate": 0.0,
                "total_return_pct": 0.0,
                "avg_gain_pct": 0.0,
                "avg_loss_pct": 0.0,
                "max_drawdown_pct": 0.0,
            },
        }

    from tools.generate_signals import generate_signal

    closes = df["Close"].values
    if hasattr(df.index, "strftime"):
        dates = df.index.strftime("%Y-%m-%d").tolist()
    else:
        dates = [str(d)[:10] for d in df.index]

    # ── Rolling signal generation ────────────────────────────────────────────
    signals: list[str] = []
    for i in range(WARMUP, len(df)):
        try:
            sig = generate_signal(df.iloc[: i + 1])["signal"]
        except Exception:
            sig = "HOLD"
        signals.append(sig)

    # ── Trade simulation ─────────────────────────────────────────────────────
    trades: list[dict] = []
    state = "flat"
    entry_price = 0.0
    entry_date = ""

    for i, sig in enumerate(signals):
        row_idx = WARMUP + i
        close = float(closes[row_idx])
        date = dates[row_idx]

        if state == "flat" and sig == "BUY":
            state = "long"
            entry_price = close
            entry_date = date

        elif state == "long" and sig == "SELL":
            pnl_pct = (close - entry_price) / entry_price * 100
            trades.append(
                {
                    "date_entry":   entry_date,
                    "date_exit":    date,
                    "entry_price":  round(entry_price, 2),
                    "exit_price":   round(close, 2),
                    "pnl_pct":      round(pnl_pct, 2),
                }
            )
            state = "flat"

    # Close any open position at the final bar
    if state == "long":
        close = float(closes[-1])
        pnl_pct = (close - entry_price) / entry_price * 100
        trades.append(
            {
                "date_entry":   entry_date,
                "date_exit":    dates[-1],
                "entry_price":  round(entry_price, 2),
                "exit_price":   round(close, 2),
                "pnl_pct":      round(pnl_pct, 2),
            }
        )

    # ── Equity curve (daily mark-to-market) ──────────────────────────────────
    # Walk every bar: flat periods hold equity constant; open positions show
    # unrealized P&L daily using that bar's close price.
    committed_equity = 100.0   # equity locked in after each trade closes
    equity_curve: list[dict] = []

    # Rebuild state by replaying signals to get daily MTM equity
    mtm_state = "flat"
    mtm_entry_price = 0.0

    for i, sig in enumerate(signals):
        row_idx = WARMUP + i
        close = float(closes[row_idx])
        date = dates[row_idx]

        if mtm_state == "flat" and sig == "BUY":
            mtm_state = "long"
            mtm_entry_price = close

        elif mtm_state == "long" and sig == "SELL":
            committed_equity *= (close / mtm_entry_price)
            mtm_state = "flat"

        # Daily equity: committed * unrealized multiplier if in a position
        if mtm_state == "long":
            daily_eq = committed_equity * (close / mtm_entry_price)
        else:
            daily_eq = committed_equity

        equity_curve.append({"date": date, "equity": round(daily_eq, 2)})

    # Force-close open position at last bar (matches trade simulation above)
    if mtm_state == "long":
        committed_equity *= float(closes[-1]) / mtm_entry_price

    equity = committed_equity

    # ── Aggregate stats ───────────────────────────────────────────────────────
    num_trades = len(trades)
    if num_trades == 0:
        return {
            "trades": [],
            "equity_curve": equity_curve,
            "stats": {
                "num_trades": 0,
                "win_rate": 0.0,
                "total_return_pct": 0.0,
                "avg_gain_pct": 0.0,
                "avg_loss_pct": 0.0,
                "max_drawdown_pct": 0.0,
            },
        }

    wins   = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]
    total_return_pct = equity - 100.0
    avg_gain_pct = sum(t["pnl_pct"] for t in wins)   / len(wins)   if wins   else 0.0
    avg_loss_pct = sum(t["pnl_pct"] for t in losses) / len(losses) if losses else 0.0

    peak = 100.0
    max_dd = 0.0
    for point in equity_curve:
        if point["equity"] > peak:
            peak = point["equity"]
        dd = (point["equity"] - peak) / peak * 100
        if dd < max_dd:
            max_dd = dd

    return {
        "trades": trades,
        "equity_curve": equity_curve,
        "stats": {
            "num_trades":       num_trades,
            "win_rate":         round(len(wins) / num_trades, 3),
            "total_return_pct": round(total_return_pct, 2),
            "avg_gain_pct":     round(avg_gain_pct, 2),
            "avg_loss_pct":     round(avg_loss_pct, 2),
            "max_drawdown_pct": round(max_dd, 2),
        },
    }
