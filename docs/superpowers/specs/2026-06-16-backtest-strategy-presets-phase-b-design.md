# Backtest Strategy Presets (Phase B) — Design Spec

**Date:** 2026-06-16
**Status:** Approved (design); pending implementation plan
**Owner:** Divyanshu
**Builds on:** Backtest Engine v2 (Phase A, shipped) — `tools/backtester.py`

## 1. Summary

Add three selectable technical-strategy presets to the backtester — **trend-following**,
**mean-reversion**, and **breakout** — alongside the existing `indicator` and `ml`
strategies. Each preset is only a **signal generator** (emits BUY/HOLD/SELL per bar);
it plugs into the **same v2 engine** built in Phase A, so the uptrend filter, ATR
stop-loss (capped at 10%), 1:3 take-profit, SELL-signal exit, 1%-risk position sizing,
open-position readout, and metrics all apply unchanged.

## 2. Goals / Non-goals

**Goals**
- Three new `strategy` values: `trend`, `meanrev`, `breakout`.
- Each is a pure per-bar signal generator reusing `compute_all` indicator columns.
- Refactor `run_backtest`'s ad-hoc strategy `if/else` into a small **registry**
  (`name → (signal_fn, warmup)`) that also drives validation and descriptions.
- Uniform v2 risk management across all five strategies (no per-strategy exit logic).
- Frontend strategy selector + type gains the three options.

**Non-goals (Phase B)**
- No change to the v2 engine (`_simulate`, `_compute_stats`, exits, sizing).
- No parameter optimization / tuning sweeps (defaults are fixed, documented constants).
- No short-selling or new exit types.
- No new indicators in `compute_indicators` — reuse existing columns; compute the
  Donchian channel inline in the breakout generator.

## 3. Strategy Registry

Replace the current `warmup = ML_WARMUP if strategy == "ml" else WARMUP` and the
`_ml_signals if strategy == "ml" else _indicator_signals` selection with a registry:

```python
STRATEGIES = {
    "indicator": (_indicator_signals, WARMUP),     # 50
    "ml":        (_ml_signals,        ML_WARMUP),  # 120
    "trend":     (_trend_signals,     TREND_WARMUP),   # 200 (EMA-200 seasoning)
    "meanrev":   (_meanrev_signals,   WARMUP),     # 50
    "breakout":  (_breakout_signals,  WARMUP),     # 50
}
```

`run_backtest(df, strategy)`: validate `strategy in STRATEGIES` (else `ValueError`),
look up `(signal_fn, warmup)`, compute `signals = signal_fn(df, warmup)`, then run the
existing v2 pipeline (`_atr`/`_ema`/`_simulate`/`_compute_stats`) unchanged. The
existing `ml` short-history guard stays; the generic `len(df) < warmup + 2` guard
covers the rest (so `trend` needs ≥ 202 bars → use a 1y/2y period).

New constant: `TREND_WARMUP = 200`.

## 4. The Three Presets (signal generators)

Each function mirrors `_indicator_signals(df, warmup)`: returns a `list[str]` of
BUY/HOLD/SELL, one per bar from index `warmup` to the end. All reuse `compute_all`
columns (`EMA_50`, `EMA_200`, `RSI_14`) except the Donchian channel (computed inline).

### 4.1 `_trend_signals` — Trend-following (EMA-50 / EMA-200)
Per bar i: `BUY` if `EMA_50[i] > EMA_200[i]`, else `SELL`. The engine enters at the
golden cross and exits at the death cross (or earlier on stop/target). Default
columns `EMA_50`, `EMA_200`. Warmup 200.

### 4.2 `_meanrev_signals` — Mean-reversion (RSI-14)
Per bar i: `BUY` if `RSI_14[i] < 30` (oversold); `SELL` if `RSI_14[i] > 55`
(reverted to mean); else `HOLD`. The engine's uptrend filter (close > EMA-200) makes
this "buy oversold dips **in uptrends**." Warmup 50.

### 4.3 `_breakout_signals` — Breakout (Donchian 20/10)
Compute prior-window channel **excluding the current bar** (no look-ahead):
`upper = High.rolling(20).max().shift(1)`, `lower = Low.rolling(10).min().shift(1)`.
Per bar i: `BUY` if `Close[i] > upper[i]`; `SELL` if `Close[i] < lower[i]`; else `HOLD`.
Warmup 50.

**Defaults as named constants** (in `backtester.py`):
```python
TREND_FAST_EMA = 50;  TREND_SLOW_EMA = 200
MEANREV_RSI_BUY = 30; MEANREV_RSI_SELL = 55
BREAKOUT_HIGH_LOOKBACK = 20; BREAKOUT_LOW_LOOKBACK = 10
```
If a needed column is missing (e.g. `EMA_50`/`RSI_14` not in the frame), the generator
falls back to `HOLD` for that bar (mirrors `_indicator_signals`' try/except robustness).

## 5. Descriptions

Add `STRATEGY_DESCRIPTIONS` entries for the three, each ending with the shared v2
risk-management sentence (uptrend gate, 2·ATR stop capped at 10%, 1:3 target,
SELL-signal exit, 1% sizing) — consistent with the existing two.

## 6. Backend Endpoint

`/api/v1/analysis/backtest` already takes `strategy` as a validated query param:
`_STRATEGY = Query("indicator", pattern=r"^(indicator|ml)$")`. **Widen the regex** to
`^(indicator|ml|trend|meanrev|breakout)$`. No other router change; `run_backtest`
handles the rest and the result shape is unchanged.

## 7. Frontend

- `frontend/src/lib/api/analysis.ts`: extend
  `BacktestStrategy = "indicator" | "ml" | "trend" | "meanrev" | "breakout"`.
- `frontend/src/components/analysis/BacktestPanel.tsx`: add three buttons to the
  existing strategy selector (labels e.g. "Trend", "Mean-Rev", "Breakout"), mirroring
  the current `indicator`/`ml` button markup + `onStrategyChange` handler. The
  per-strategy `strategy_description` already renders from the response.

## 8. Testing (pytest, `tests/test_backtester.py`)

Append (plain pytest functions alongside the existing ones):
- `_trend_signals`: on a frame where `EMA_50 > EMA_200`, bars emit BUY; where below, SELL.
- `_meanrev_signals`: RSI < 30 → BUY; RSI > 55 → SELL; mid → HOLD (build a frame with a
  known RSI_14 column, or synthetic prices that produce oversold/overbought).
- `_breakout_signals`: a close above the prior-20-day high → BUY; below the prior-10-day
  low → SELL; the channel must exclude the current bar (no look-ahead).
- `run_backtest` end-to-end for each of `trend`/`meanrev`/`breakout` on a synthetic
  frame: `error is None`, result has the v2 shape (`open_position`, stats keys,
  per-trade `exit_reason`), and `strategy` echoes back.
- Registry/dispatch: an unknown strategy still raises `ValueError`; `indicator` and `ml`
  still run (no regression).

Backend: extend `backend/tests/test_analysis_backtest.py` to assert one preset
(e.g. `trend`) returns the v2 shape.

## 9. File Structure
- `tools/backtester.py` — 3 new signal generators + `TREND_WARMUP` + preset constants +
  `STRATEGIES` registry + `run_backtest` dispatch + 3 `STRATEGY_DESCRIPTIONS` entries.
- `tests/test_backtester.py` — preset signal + end-to-end tests.
- `backend/routers/analysis.py` — widen the `strategy` query regex.
- `backend/tests/test_analysis_backtest.py` — one preset shape test.
- `frontend/src/lib/api/analysis.ts` — `BacktestStrategy` union.
- `frontend/src/components/analysis/BacktestPanel.tsx` — selector buttons.
- `README.md` — list the five strategies under Backtesting.

## 10. Out of Scope (future)
- Per-strategy parameter UI / optimization.
- Additional presets (momentum, pairs, volatility).
- Per-strategy exit overrides (all use the shared v2 exits by design).
