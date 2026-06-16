# Backtest Engine v2 (Phase A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the walk-forward backtester with risk-managed exits (ATR stop-loss, 1:3 take-profit, trailing stop), a trend filter on entries, fixed-fractional position sizing, richer metrics, and a real currently-open-position readout — for both `indicator` and `ml` strategies.

**Architecture:** Keep `tools/backtester.py`'s single-pass design but extract the trade state machine into a pure `_simulate(...)` function (testable with synthetic arrays). `run_backtest` computes ATR(14) + EMA(200) from the OHLCV frame, builds per-bar signals (unchanged), runs `_simulate`, and assembles an extended result (`open_position`, per-trade `exit_reason`/`r_multiple`, new stats). The backend endpoint and result shape are extended (backward-compatible); the frontend gains an open-position card, new metric cards, and an exit-reason column.

**Tech Stack:** Python · numpy · pandas · pytest · Next.js / TypeScript (TanStack Query).

**Reference spec:** `docs/superpowers/specs/2026-06-15-backtest-engine-v2-design.md`

---

## File Structure

**Modify:**
- `tools/backtester.py` — add ATR/EMA helpers, the pure `_simulate`, extended `_compute_stats`, rewired `run_backtest`, updated `STRATEGY_DESCRIPTIONS` + param constants.
- `tests/test_backtester.py` — **create** (no dedicated test today); unit-tests the helpers, simulator (each exit type), metrics, and an integration run.
- `backend/tests/test_analysis_backtest.py` — **create**; endpoint smoke test that the extended fields surface.
- `frontend/src/lib/api/analysis.ts` — extend `BacktestStats`, `BacktestTrade`; add `OpenPosition`; add `open_position` to `BacktestResponse`.
- `frontend/src/components/analysis/BacktestPanel.tsx` — open-position card, new metric cards, exit-reason column, methodology note.
- `README.md` — update the Backtesting section.

**Existing behavior reused as-is:** `_indicator_signals`, `_ml_signals`, `_empty_result`, `_max_drawdown`, the warmup constants, and `/api/v1/analysis/backtest` (signature unchanged).

---

## Task 1: ATR(14) + EMA(200) helpers

Self-contained indicator helpers so the backtester doesn't depend on `compute_all`'s column naming.

**Files:**
- Modify: `tools/backtester.py`
- Test: `tests/test_backtester.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_backtester.py`:

```python
import numpy as np
import pandas as pd
from tools.backtester import _atr, _ema


def _df(highs, lows, closes):
    idx = pd.date_range("2025-01-01", periods=len(closes), freq="D")
    return pd.DataFrame({"High": highs, "Low": lows, "Close": closes}, index=idx)


def test_atr_is_positive_and_aligned():
    n = 30
    closes = list(np.linspace(100, 130, n))
    highs = [c + 2 for c in closes]
    lows = [c - 2 for c in closes]
    atr = _atr(_df(highs, lows, closes), period=14)
    assert len(atr) == n
    # after the warmup period ATR is finite and positive
    assert atr[20] > 0
    assert np.isfinite(atr[20])


def test_ema_tracks_level():
    closes = np.array([10.0] * 50)
    ema = _ema(closes, 200)
    assert len(ema) == 50
    assert abs(ema[-1] - 10.0) < 1e-6   # constant series -> EMA equals the level
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_backtester.py -v`
Expected: FAIL — `ImportError: cannot import name '_atr'`

- [ ] **Step 3: Implement (add near the top of `tools/backtester.py`, after the existing constants)**

Add these parameter constants and helpers:

```python
# ── v2 risk-management parameters ────────────────────────────────────────────
TREND_EMA = 200       # only enter long when close > EMA(200)
ATR_PERIOD = 14
SL_ATR_MULT = 2.0     # initial stop = entry − 2.0·ATR
RR_RATIO = 3.0        # target = entry + RR_RATIO·risk  → 1:3 minimum reward:risk
TRAIL_ATR_MULT = 2.5  # trailing stop = highest-close-since-entry − 2.5·ATR
RISK_PCT = 0.01       # risk 1% of equity to the stop per trade


def _atr(df: pd.DataFrame, period: int = ATR_PERIOD) -> np.ndarray:
    """Average True Range as a numpy array aligned to df (Wilder-style SMA of TR)."""
    high = df["High"].astype(float).values
    low = df["Low"].astype(float).values
    close = df["Close"].astype(float).values
    prev_close = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum.reduce([
        high - low,
        np.abs(high - prev_close),
        np.abs(low - prev_close),
    ])
    tr_s = pd.Series(tr)
    atr = tr_s.rolling(period, min_periods=1).mean().values
    return atr


def _ema(values: np.ndarray, period: int) -> np.ndarray:
    """Exponential moving average aligned to `values`."""
    return pd.Series(values, dtype=float).ewm(span=period, adjust=False).mean().values
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_backtester.py -v`
Expected: PASS

- [ ] **Step 5: Syntax check + commit**

```bash
python -c "import py_compile; py_compile.compile('tools/backtester.py', doraise=True)"
git add tools/backtester.py tests/test_backtester.py
git commit -m "feat(backtest): ATR + EMA helpers for v2 engine"
```

---

## Task 2: The v2 simulator (`_simulate`)

A pure state machine over aligned arrays: trend-filtered entries, fixed-fractional sizing, and stop / target / trailing / signal exits, returning closed trades, the daily equity curve, and any open position.

**Files:**
- Modify: `tools/backtester.py`
- Test: `tests/test_backtester.py` (append)

- [ ] **Step 1: Append the failing tests**

```python
from tools.backtester import _simulate


def _const_atr(n, val=10.0):
    return np.array([val] * n, dtype=float)


def _dates(n):
    return pd.date_range("2025-01-01", periods=n, freq="D").strftime("%Y-%m-%d").tolist()


def test_trend_filter_blocks_counter_trend_buy():
    # close below EMA-trend on the BUY bar -> no entry
    closes = np.array([100.0, 100.0, 100.0])
    ema = np.array([110.0, 110.0, 110.0])      # price below trend
    out = _simulate(_dates(3), closes, _const_atr(3), ema, ["HOLD", "BUY", "HOLD"])
    assert out["trades"] == []
    assert out["open_position"] is None


def test_stop_loss_exit():
    # entry 100, ATR 10 -> stop = 100 - 2*10 = 80; price falls to 79 -> stop hit
    closes = np.array([100.0, 95.0, 79.0])
    ema = np.array([90.0, 90.0, 90.0])         # uptrend (close > ema at entry)
    out = _simulate(_dates(3), closes, _const_atr(3), ema, ["BUY", "HOLD", "HOLD"])
    assert len(out["trades"]) == 1
    assert out["trades"][0]["exit_reason"] == "stop"
    assert out["open_position"] is None


def test_take_profit_exit_hits_1to3():
    # entry 100, stop 80, risk 20, target = 100 + 3*20 = 160; price reaches 160
    closes = np.array([100.0, 130.0, 160.0])
    ema = np.array([90.0, 90.0, 90.0])
    out = _simulate(_dates(3), closes, _const_atr(3), ema, ["BUY", "HOLD", "HOLD"])
    assert len(out["trades"]) == 1
    t = out["trades"][0]
    assert t["exit_reason"] == "target"
    assert round(t["r_multiple"], 1) == 3.0


def test_trailing_stop_exit_locks_gain():
    # run up to 150 (high), trail = 150 - 2.5*10 = 125; pullback to 124 -> trail exit (> initial stop 80)
    closes = np.array([100.0, 150.0, 124.0])
    ema = np.array([90.0, 90.0, 90.0])
    out = _simulate(_dates(3), closes, _const_atr(3), ema, ["BUY", "HOLD", "HOLD"])
    assert len(out["trades"]) == 1
    t = out["trades"][0]
    assert t["exit_reason"] == "trail"
    assert t["pnl_pct"] > 0


def test_sell_signal_exit():
    # price stays between stop and target; SELL closes it
    closes = np.array([100.0, 105.0, 108.0])
    ema = np.array([90.0, 90.0, 90.0])
    out = _simulate(_dates(3), closes, _const_atr(3), ema, ["BUY", "HOLD", "SELL"])
    assert len(out["trades"]) == 1
    assert out["trades"][0]["exit_reason"] == "signal"


def test_open_position_reported_when_ending_long():
    closes = np.array([100.0, 105.0, 108.0])
    ema = np.array([90.0, 90.0, 90.0])
    out = _simulate(_dates(3), closes, _const_atr(3), ema, ["BUY", "HOLD", "HOLD"])
    assert out["trades"] == []                 # not force-closed
    op = out["open_position"]
    assert op is not None
    assert op["entry_price"] == 100.0
    assert op["current_price"] == 108.0
    assert round(op["unrealized_pnl_pct"], 1) == 8.0
    assert op["stop"] == 80.0 and op["target"] == 160.0


def test_position_sizing_scales_with_stop_distance():
    # Tight stop (small ATR) allocates more than a wide stop, for the same +X% move.
    closes = np.array([100.0, 110.0])
    ema = np.array([90.0, 90.0])
    tight = _simulate(_dates(2), closes, _const_atr(2, 2.5), ema, ["BUY", "SELL"])
    wide = _simulate(_dates(2), closes, _const_atr(2, 25.0), ema, ["BUY", "SELL"])
    # both win the same % move, but the tight-stop trade commits more equity -> bigger equity gain
    assert tight["equity_curve"][-1]["equity"] > wide["equity_curve"][-1]["equity"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_backtester.py -k simulate -v` (and the new functions)
Expected: FAIL — `ImportError: cannot import name '_simulate'`

- [ ] **Step 3: Implement `_simulate` (add to `tools/backtester.py`)**

```python
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
    stop = target = init_risk = atr_entry = entry_high = 0.0
    bars_long = 0

    for i, sig in enumerate(signals):
        close = float(closes[i])
        date = dates[i]

        # ── exit checks (while long) ─────────────────────────────────────────
        if state == "long":
            entry_high = max(entry_high, close)
            trail = entry_high - TRAIL_ATR_MULT * atr_entry
            eff_stop = max(stop, trail)
            exit_reason = None
            if close <= eff_stop:
                exit_reason = "trail" if eff_stop > stop else "stop"
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
                    "r_multiple":  round((close - entry_price) / init_risk, 2) if init_risk else 0.0,
                })
                invested = 0.0
                state = "flat"

        # ── entry (flat + BUY + uptrend) ─────────────────────────────────────
        if state == "flat" and sig == "BUY" and close > float(ema_trend[i]):
            atr_entry = float(atr[i])
            if atr_entry > 0:
                stop = close - SL_ATR_MULT * atr_entry
                init_risk = close - stop
                target = close + RR_RATIO * init_risk
                stop_dist_pct = init_risk / close
                alloc = min(1.0, RISK_PCT / stop_dist_pct) if stop_dist_pct > 0 else 0.0
                equity = cash                                   # flat -> equity == cash
                invested = alloc * equity
                cash = equity - invested
                entry_price = close
                entry_date = date
                entry_high = close
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
            "days_held":          (pd.Timestamp(dates[-1]) - pd.Timestamp(entry_date)).days,
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_backtester.py -v`
Expected: all PASS

- [ ] **Step 5: Syntax check + commit**

```bash
python -c "import py_compile; py_compile.compile('tools/backtester.py', doraise=True)"
git add tools/backtester.py tests/test_backtester.py
git commit -m "feat(backtest): v2 simulator — trend filter, sizing, stop/target/trail exits, open position"
```

---

## Task 3: Richer metrics

Extend `_compute_stats` with CAGR, Sortino, Calmar, best/worst trade, and max consecutive losses.

**Files:**
- Modify: `tools/backtester.py`
- Test: `tests/test_backtester.py` (append)

- [ ] **Step 1: Append the failing test**

```python
from tools.backtester import _compute_stats


def test_richer_metrics_present_and_sane():
    trades = [
        {"date_entry": "2025-01-01", "date_exit": "2025-01-05", "pnl_pct": 5.0},
        {"date_entry": "2025-01-06", "date_exit": "2025-01-08", "pnl_pct": -2.0},
        {"date_entry": "2025-01-09", "date_exit": "2025-01-12", "pnl_pct": -1.0},
    ]
    curve = [{"date": f"2025-01-{d:02d}", "equity": e, "benchmark": 100.0}
             for d, e in zip(range(1, 7), [100, 102, 105, 103, 104, 108])]
    s = _compute_stats(trades, curve, final_equity=108.0, bars_long=4,
                       n_signal_bars=6, buy_hold_return_pct=8.0)
    assert s["best_trade_pct"] == 5.0
    assert s["worst_trade_pct"] == -2.0
    assert s["max_consecutive_losses"] == 2
    assert "cagr_pct" in s and "sortino_ratio" in s and "calmar_ratio" in s
    assert s["cagr_pct"] > 0          # ended at 108 from 100
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_backtester.py -k richer_metrics -v`
Expected: FAIL — `KeyError: 'best_trade_pct'`

- [ ] **Step 3: Implement — replace the `return {...}` block at the end of `_compute_stats`**

Add these computations just before the existing `return {` in `_compute_stats`, then extend the returned dict:

```python
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

    max_dd = _max_drawdown(equity_curve)
    calmar = round(cagr / abs(max_dd), 2) if max_dd < 0 else None

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
```

Then add these keys to the returned dict (alongside the existing ones):

```python
        "cagr_pct":               cagr,
        "sortino_ratio":          sortino,
        "calmar_ratio":           calmar,
        "best_trade_pct":         best_trade,
        "worst_trade_pct":        worst_trade,
        "max_consecutive_losses": max_consec,
```

(Note: `eq` and `_max_drawdown` are already computed earlier in `_compute_stats`; reuse them — do not recompute `eq`.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_backtester.py -v`
Expected: all PASS

- [ ] **Step 5: Syntax check + commit**

```bash
python -c "import py_compile; py_compile.compile('tools/backtester.py', doraise=True)"
git add tools/backtester.py tests/test_backtester.py
git commit -m "feat(backtest): CAGR, Sortino, Calmar, best/worst trade, max consec losses"
```

---

## Task 4: Rewire `run_backtest`

Wire the helpers + signals + `_simulate` together and assemble the extended result.

**Files:**
- Modify: `tools/backtester.py`
- Test: `tests/test_backtester.py` (append)

- [ ] **Step 1: Append the failing integration test**

```python
from tools.backtester import run_backtest


def _trending_df(n=120):
    idx = pd.date_range("2025-01-01", periods=n, freq="D")
    closes = np.linspace(100, 200, n)          # steady uptrend
    return pd.DataFrame({
        "Open": closes, "High": closes + 1, "Low": closes - 1,
        "Close": closes, "Volume": [1_000_000] * n,
    }, index=idx)


def test_run_backtest_v2_contract():
    res = run_backtest(_trending_df(), strategy="indicator")
    assert res["error"] is None
    # extended result keys present
    assert "open_position" in res
    for k in ("cagr_pct", "sortino_ratio", "calmar_ratio",
              "best_trade_pct", "worst_trade_pct", "max_consecutive_losses"):
        assert k in res["stats"]
    # closed trades carry an exit reason
    for t in res["trades"]:
        assert t["exit_reason"] in ("stop", "target", "trail", "signal")
        assert "r_multiple" in t
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_backtester.py -k v2_contract -v`
Expected: FAIL — `KeyError: 'open_position'` (run_backtest not rewired yet)

- [ ] **Step 3: Rewire `run_backtest`**

Replace the body of `run_backtest` from the `closes = df["Close"].values` line through the final `return {...}` with:

```python
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
```

Also update `_empty_result` to include `"open_position": None` so the empty shape matches:

```python
        "trades": [],
        "open_position": None,
        "equity_curve": [],
```

And update `STRATEGY_DESCRIPTIONS` so both entries mention the v2 mechanics — append to each description string:

```
" Entries require an uptrend (close > EMA-200); exits on a 2·ATR stop, "
"1:3 ATR take-profit, 2.5·ATR trailing stop, or the strategy's SELL signal; "
"positions are risk-sized to 1% of equity."
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_backtester.py -v`
Expected: all PASS

- [ ] **Step 5: Syntax check + commit**

```bash
python -c "import py_compile; py_compile.compile('tools/backtester.py', doraise=True)"
git add tools/backtester.py tests/test_backtester.py
git commit -m "feat(backtest): rewire run_backtest to v2 engine + extended result"
```

---

## Task 5: Backend endpoint smoke test

The `/analysis/backtest` route already passes `run_backtest(...)` through `clean_dict`; no router code changes. Add a test that the extended fields survive serialization.

**Files:**
- Create: `backend/tests/test_analysis_backtest.py`

- [ ] **Step 1: Write the test**

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import numpy as np
import pandas as pd
import pytest
from tools import backtester


def test_backtest_result_has_v2_fields():
    n = 120
    closes = np.linspace(100, 200, n)
    df = pd.DataFrame({
        "Open": closes, "High": closes + 1, "Low": closes - 1,
        "Close": closes, "Volume": [1_000_000] * n,
    }, index=pd.date_range("2025-01-01", periods=n, freq="D"))
    res = backtester.run_backtest(df, strategy="indicator")
    assert "open_position" in res
    assert {"cagr_pct", "sortino_ratio", "calmar_ratio"} <= set(res["stats"])
```

- [ ] **Step 2: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_analysis_backtest.py -v`
Expected: PASS (run_backtest already returns the v2 shape).

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_analysis_backtest.py
git commit -m "test(backtest): endpoint-level v2 result shape"
```

---

## Task 6: Frontend types

**Files:**
- Modify: `frontend/src/lib/api/analysis.ts`

- [ ] **Step 1: Extend the backtest types**

Add `exit_reason`/`r_multiple` to `BacktestTrade`:
```typescript
export interface BacktestTrade {
  date_entry: string;
  date_exit: string;
  entry_price: number;
  exit_price: number;
  pnl_pct: number;
  exit_reason: "stop" | "target" | "trail" | "signal";
  r_multiple: number;
}
```

Add the new stat fields to `BacktestStats`:
```typescript
  cagr_pct: number;
  sortino_ratio: number;
  calmar_ratio: number | null;
  best_trade_pct: number;
  worst_trade_pct: number;
  max_consecutive_losses: number;
```

Add an `OpenPosition` interface and `open_position` to `BacktestResponse`:
```typescript
export interface OpenPosition {
  date_entry: string;
  entry_price: number;
  current_price: number;
  unrealized_pnl_pct: number;
  days_held: number;
  stop: number;
  target: number;
  exit_reason: null;
}
```
and in `BacktestResponse` add: `open_position: OpenPosition | null;`

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: errors ONLY in `BacktestPanel.tsx` (consuming the new fields) — fixed in Task 7. If `analysis.ts` itself errors, fix it.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/api/analysis.ts
git commit -m "feat(backtest): frontend types for open position + v2 metrics"
```

---

## Task 7: Frontend — open-position card, metrics, exit column

> **READ FIRST:** `frontend/AGENTS.md` — read the relevant Next docs and mirror the existing `BacktestPanel.tsx` patterns (stat-card markup, color tokens `text-buy`/`text-sell`/`text-hold`, the trades table). Do not hand-write from memory.

**Files:**
- Modify: `frontend/src/components/analysis/BacktestPanel.tsx`

- [ ] **Step 1: Open-position card** — when `data.open_position` is non-null, render a card **above the equity chart**, visually distinct (e.g. an accent border). Show: "Open position" heading, entry date + `entry_price`, `current_price`, `unrealized_pnl_pct` (green if ≥0 else red), `days_held`, and `stop` / `target` with the % distance from current price. Mirror the existing stat-card container styling already in this file.

- [ ] **Step 2: New metric cards** — in the existing stats grid, add CAGR (`cagr_pct`%), Sortino (`sortino_ratio`), and Calmar (`calmar_ratio`, show "—" when null), using the same stat-card component/markup as Max Drawdown/Sharpe/etc.

- [ ] **Step 3: Exit-reason column** — add an "Exit" column to the trades table rendering `trade.exit_reason` (Stop / Target / Trail / Signal), colored subtly: target = `text-buy`, stop/trail = `text-sell`, signal = muted. Keep the existing columns.

- [ ] **Step 4: Methodology note** — update the "How this backtest works" copy to describe: uptrend-only entries (EMA-200), 2·ATR stop, **1:3** ATR take-profit, 2.5·ATR trailing stop, SELL-signal exit, and 1%-risk position sizing.

- [ ] **Step 5: Type-check + build**

Run: `cd frontend && npx tsc --noEmit && npx next build --webpack`
Expected: clean; `/dashboard/stocks/[ticker]` route builds. (Local default `npm run build` uses Turbopack which fails on darwin/arm64 — use `--webpack`; CI/Linux is fine.)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/analysis/BacktestPanel.tsx
git commit -m "feat(backtest): open-position card, CAGR/Sortino/Calmar, exit-reason column"
```

---

## Task 8: Docs

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update the Backtesting section** to describe v2: uptrend-only entries (EMA-200), ATR stop-loss (2·ATR), **1:3** ATR take-profit, 2.5·ATR trailing stop, SELL-signal exit, 1%-risk fixed-fractional sizing, the currently-open-position readout, and the added metrics (CAGR/Sortino/Calmar/best-worst/max-consecutive-losses). Note these apply to both `indicator` and `ml` strategies; new strategy presets are a planned Phase B.

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs(backtest): document v2 engine (stops, sizing, open position, metrics)"
```

---

## Task 9: Final verification

- [ ] **Step 1: Python suites**

Run: `python -m pytest tests/test_backtester.py -v && (cd backend && python -m pytest tests/test_analysis_backtest.py -v)`
Expected: all PASS.

- [ ] **Step 2: Frontend gates**

Run: `cd frontend && npx tsc --noEmit && npm run lint`
Expected: clean.

- [ ] **Step 3: Live smoke (optional)**

With the backend (anaconda python) + frontend running, open `/dashboard/stocks/HDFCBANK.NS`, scroll to Backtest: confirm the trades table shows exit reasons, CAGR/Sortino/Calmar appear, and if a position is open you see the Open-position card (the old "force-closed last trade" should now be the open position instead).

- [ ] **Step 4: Final commit (if tweaks remain)**

```bash
git add -A && git commit -m "chore(backtest): v2 verification"
```

---

## Out of Scope (Phase B — separate plan)
- New selectable strategy presets: trend-following (MA crossover), mean-reversion (RSI bounce), breakout (Donchian/52-week).
- Transaction costs / slippage; intraday/gap fills; multiple concurrent positions.
