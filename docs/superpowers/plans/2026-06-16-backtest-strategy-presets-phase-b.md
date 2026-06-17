# Backtest Strategy Presets (Phase B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three selectable technical-strategy presets — `trend` (EMA-50/200), `meanrev` (RSI-14), `breakout` (Donchian 20/10) — that run on the existing v2 backtest engine.

**Architecture:** Each preset is a pure per-bar signal generator (`_<name>_signals(df, warmup) -> list[str]`), exactly like `_indicator_signals`. A `STRATEGIES` registry (`name -> (signal_fn, warmup)`) replaces the ad-hoc `if strategy=="ml"` dispatch in `run_backtest`; the v2 engine (`_simulate`: uptrend filter, 10%-capped ATR stop, 1:3 target, SELL exit, 1%-risk sizing) applies unchanged to all five strategies. Backend widens the `strategy` query regex; frontend adds three selector options.

**Tech Stack:** Python · pandas · pytest · Next.js / TypeScript.

**Reference spec:** `docs/superpowers/specs/2026-06-16-backtest-strategy-presets-phase-b-design.md`

**Builds on:** Backtest Engine v2 (shipped) — `tools/backtester.py` has `_atr`, `_ema`, `_simulate`, `_compute_stats`, `_indicator_signals`, `_ml_signals`, `run_backtest`, `STRATEGY_DESCRIPTIONS`.

---

## File Structure

**Modify:**
- `tools/backtester.py` — 3 signal generators + preset constants + `STRATEGIES` registry + `run_backtest` dispatch + 3 `STRATEGY_DESCRIPTIONS` entries.
- `tests/test_backtester.py` — generator unit tests + per-preset end-to-end tests (append plain pytest functions; the file already mixes unittest classes + pytest functions).
- `backend/routers/analysis.py` — widen the `_STRATEGY` query regex.
- `backend/tests/test_analysis_backtest.py` — one preset shape test.
- `frontend/src/lib/api/analysis.ts` — extend `BacktestStrategy`.
- `frontend/src/components/analysis/BacktestPanel.tsx` — add 3 selector buttons.
- `README.md` — list the five strategies.

**Conventions:** signal generators mirror `_indicator_signals` — loop `range(warmup, len(df))`, append one of `"BUY"/"HOLD"/"SELL"` per bar, wrap per-bar logic in `try/except` → `"HOLD"` (robust to missing columns / NaN). They reuse `compute_all` columns (`EMA_50`, `EMA_200`, `RSI_14`); breakout computes its Donchian channel inline. `numpy as np` / `pandas as pd` are already imported.

---

## Task 1: `_trend_signals` (EMA-50 / EMA-200 trend-following)

**Files:**
- Modify: `tools/backtester.py`
- Test: `tests/test_backtester.py`

- [ ] **Step 1: Append the failing test**

```python
from tools.backtester import _trend_signals


def test_trend_signals_buy_above_sell_below():
    df = pd.DataFrame({
        "EMA_50":  [1.0, 2.0, 3.0, 4.0, 5.0],
        "EMA_200": [3.0, 3.0, 3.0, 3.0, 3.0],
    })
    # fast>slow only at i3 (4>3) and i4 (5>3); i2 is 3>3 -> False -> SELL
    assert _trend_signals(df, warmup=0) == ["SELL", "SELL", "SELL", "BUY", "BUY"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_backtester.py -k trend_signals -v`
Expected: FAIL — `ImportError: cannot import name '_trend_signals'`

- [ ] **Step 3: Implement — add to `tools/backtester.py`** (after `_ml_signals`, with the other signal generators)

```python
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_backtester.py -k trend_signals -v`
Expected: PASS

- [ ] **Step 5: Syntax check + commit**

```bash
python -c "import py_compile; py_compile.compile('tools/backtester.py', doraise=True)"
git add tools/backtester.py tests/test_backtester.py
git commit -m "feat(backtest): trend-following signal generator (EMA-50/200)"
```

---

## Task 2: `_meanrev_signals` (RSI-14 mean-reversion)

**Files:**
- Modify: `tools/backtester.py`
- Test: `tests/test_backtester.py`

- [ ] **Step 1: Append the failing test**

```python
from tools.backtester import _meanrev_signals


def test_meanrev_signals_oversold_buy_recovered_sell():
    df = pd.DataFrame({"RSI_14": [25.0, 40.0, 60.0, 28.0, 70.0]})
    # <30 -> BUY, 30..55 -> HOLD, >55 -> SELL
    assert _meanrev_signals(df, warmup=0) == ["BUY", "HOLD", "SELL", "BUY", "SELL"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_backtester.py -k meanrev_signals -v`
Expected: FAIL — `ImportError: cannot import name '_meanrev_signals'`

- [ ] **Step 3: Implement — add to `tools/backtester.py`** (after `_trend_signals`)

```python
MEANREV_RSI_BUY = 30        # RSI below this = oversold -> BUY
MEANREV_RSI_SELL = 55       # RSI above this = reverted -> SELL


def _meanrev_signals(df: pd.DataFrame, warmup: int) -> list[str]:
    """Mean-reversion: BUY when RSI-14 < 30 (oversold), SELL when RSI-14 > 55."""
    rsi = df.get("RSI_14")
    signals: list[str] = []
    for i in range(warmup, len(df)):
        try:
            r = float(rsi.iloc[i])
            if r < MEANREV_RSI_BUY:
                signals.append("BUY")
            elif r > MEANREV_RSI_SELL:
                signals.append("SELL")
            else:
                signals.append("HOLD")
        except Exception:
            signals.append("HOLD")
    return signals
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_backtester.py -k meanrev_signals -v`
Expected: PASS

- [ ] **Step 5: Syntax check + commit**

```bash
python -c "import py_compile; py_compile.compile('tools/backtester.py', doraise=True)"
git add tools/backtester.py tests/test_backtester.py
git commit -m "feat(backtest): mean-reversion signal generator (RSI-14)"
```

---

## Task 3: `_breakout_signals` (Donchian 20/10)

**Files:**
- Modify: `tools/backtester.py`
- Test: `tests/test_backtester.py`

- [ ] **Step 1: Append the failing test**

```python
from tools.backtester import _breakout_signals


def test_breakout_signals_high_break_buys():
    # 25 flat bars at 100, then a close above the prior-20-day high -> BUY
    highs = [100.0] * 25 + [111.0]
    lows = [100.0] * 25 + [111.0]
    closes = [100.0] * 25 + [110.0]
    df = pd.DataFrame({"High": highs, "Low": lows, "Close": closes})
    sigs = _breakout_signals(df, warmup=20)
    assert sigs[-1] == "BUY"           # last bar breaks out above prior-20 high (100)
    assert set(sigs[:-1]) <= {"HOLD"}  # flat bars before the break don't signal


def test_breakout_signals_low_break_sells():
    highs = [100.0] * 25 + [100.0]
    lows = [100.0] * 25 + [88.0]
    closes = [100.0] * 25 + [89.0]     # close below prior-10-day low (100) -> SELL
    df = pd.DataFrame({"High": highs, "Low": lows, "Close": closes})
    assert _breakout_signals(df, warmup=20)[-1] == "SELL"
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_backtester.py -k breakout_signals -v`
Expected: FAIL — `ImportError: cannot import name '_breakout_signals'`

- [ ] **Step 3: Implement — add to `tools/backtester.py`** (after `_meanrev_signals`)

```python
BREAKOUT_HIGH_LOOKBACK = 20  # close above prior N-day high -> BUY
BREAKOUT_LOW_LOOKBACK = 10   # close below prior M-day low -> SELL


def _breakout_signals(df: pd.DataFrame, warmup: int) -> list[str]:
    """Breakout: BUY when close > prior-20-day high, SELL when close < prior-10-day low.

    Channels use .shift(1) so the current bar is NOT part of its own window (no look-ahead).
    """
    upper = df["High"].rolling(BREAKOUT_HIGH_LOOKBACK).max().shift(1)
    lower = df["Low"].rolling(BREAKOUT_LOW_LOOKBACK).min().shift(1)
    closes = df["Close"]
    signals: list[str] = []
    for i in range(warmup, len(df)):
        try:
            c = float(closes.iloc[i])
            if c > float(upper.iloc[i]):
                signals.append("BUY")
            elif c < float(lower.iloc[i]):
                signals.append("SELL")
            else:
                signals.append("HOLD")
        except Exception:
            signals.append("HOLD")
    return signals
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_backtester.py -k breakout_signals -v`
Expected: both PASS

- [ ] **Step 5: Syntax check + commit**

```bash
python -c "import py_compile; py_compile.compile('tools/backtester.py', doraise=True)"
git add tools/backtester.py tests/test_backtester.py
git commit -m "feat(backtest): breakout signal generator (Donchian 20/10)"
```

---

## Task 4: Strategy registry + `run_backtest` dispatch

Wire the new (and existing) signal generators into a registry and route `run_backtest` through it.

**Files:**
- Modify: `tools/backtester.py`
- Test: `tests/test_backtester.py`

- [ ] **Step 1: Append the failing end-to-end test**

```python
def test_run_backtest_presets_end_to_end():
    from tools.backtester import run_backtest
    for strat in ("trend", "meanrev", "breakout"):
        res = run_backtest(enriched(260), strategy=strat)
        assert res["error"] is None, f"{strat} errored"
        assert res["strategy"] == strat
        assert "open_position" in res
        assert {"cagr_pct", "sortino_ratio"} <= set(res["stats"])
        for t in res["trades"]:
            assert t["exit_reason"] in ("stop", "target", "signal")
```

(`enriched(n)` is the existing helper at the top of the test file — `compute_all(synthetic_ohlcv(n))` — which supplies `EMA_50`, `EMA_200`, `RSI_14`.)

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_backtester.py -k presets_end_to_end -v`
Expected: FAIL — `ValueError: Unknown strategy: 'trend'` (registry not wired yet)

- [ ] **Step 3: Add the `STRATEGIES` registry + new descriptions, and route `run_backtest`**

(a) Add three entries to `STRATEGY_DESCRIPTIONS` (the dict near the top of the file). Each should mention its own logic and end with the shared v2 sentence, e.g.:
```python
    "trend": (
        "Trend-following: long while EMA-50 is above EMA-200 (enters at the golden "
        "cross, exits at the death cross). Entries require an uptrend (close > EMA-200); "
        "exits on a 2·ATR stop (capped at 10% below entry), a 1:3 ATR take-profit, or the "
        "strategy's SELL signal; positions are risk-sized to 1% of equity."
    ),
    "meanrev": (
        "Mean-reversion: BUY when RSI-14 < 30 (oversold), SELL when RSI-14 > 55. Combined "
        "with the uptrend filter this buys dips in uptrends. Exits on a 2·ATR stop (capped "
        "at 10% below entry), a 1:3 ATR take-profit, or the SELL signal; risk-sized to 1%."
    ),
    "breakout": (
        "Breakout: BUY when price closes above its prior 20-day high, SELL when it closes "
        "below its prior 10-day low. Entries require an uptrend (close > EMA-200); exits on "
        "a 2·ATR stop (capped at 10% below entry), a 1:3 ATR take-profit, or the SELL "
        "signal; positions are risk-sized to 1% of equity."
    ),
```

(b) Define the registry IMMEDIATELY ABOVE `run_backtest` (after all signal generators are defined):
```python
# Strategy name -> (signal generator, warmup bars). The v2 engine is shared.
STRATEGIES = {
    "indicator": (_indicator_signals, WARMUP),
    "ml":        (_ml_signals,        ML_WARMUP),
    "trend":     (_trend_signals,     TREND_WARMUP),
    "meanrev":   (_meanrev_signals,   WARMUP),
    "breakout":  (_breakout_signals,  WARMUP),
}
```

(c) In `run_backtest`, replace the validation + warmup + signal-selection lines:
```python
    if strategy not in STRATEGY_DESCRIPTIONS:
        raise ValueError(f"Unknown strategy: {strategy!r}")

    warmup = ML_WARMUP if strategy == "ml" else WARMUP
```
with:
```python
    if strategy not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {strategy!r}")

    signal_fn, warmup = STRATEGIES[strategy]
```
and replace:
```python
    signals = _ml_signals(df, warmup) if strategy == "ml" else _indicator_signals(df, warmup)
```
with:
```python
    signals = signal_fn(df, warmup)
```
Leave the `ml` short-history guard, the `len(df) < warmup + 2` guard, and everything else unchanged.

- [ ] **Step 4: Run to verify it passes (and nothing regressed)**

Run: `python -m pytest tests/test_backtester.py -v`
Expected: ALL pass — the 3 preset end-to-end cases plus every existing test (`indicator`/`ml` shape, stats math, ML determinism, unknown-strategy raises). If a pre-existing test fails, STOP and report.

- [ ] **Step 5: Syntax check + commit**

```bash
python -c "import py_compile; py_compile.compile('tools/backtester.py', doraise=True)"
git add tools/backtester.py tests/test_backtester.py
git commit -m "feat(backtest): strategy registry + dispatch for the 3 presets"
```

---

## Task 5: Backend — widen the strategy query param

**Files:**
- Modify: `backend/routers/analysis.py`
- Test: `backend/tests/test_analysis_backtest.py`

- [ ] **Step 1: Add a preset shape test (append to `backend/tests/test_analysis_backtest.py`)**

```python
def test_backtest_trend_preset_shape():
    import numpy as np
    import pandas as pd
    from tools import backtester
    n = 260
    closes = np.linspace(100, 200, n)
    df = pd.DataFrame({
        "Open": closes, "High": closes + 1, "Low": closes - 1,
        "Close": closes, "Volume": [1_000_000] * n,
    }, index=pd.date_range("2025-01-01", periods=n, freq="D"))
    from tools.compute_indicators import compute_all
    res = backtester.run_backtest(compute_all(df), strategy="trend")
    assert res["error"] is None
    assert res["strategy"] == "trend"
    assert "open_position" in res
```

- [ ] **Step 2: Run to verify it passes**

Run: `cd backend && python -m pytest tests/test_analysis_backtest.py -v`
Expected: PASS (the registry from Task 4 already supports `trend`).

- [ ] **Step 3: Widen the endpoint's strategy regex in `backend/routers/analysis.py`**

Change:
```python
_STRATEGY = Query("indicator", pattern=r"^(indicator|ml)$")
```
to:
```python
_STRATEGY = Query("indicator", pattern=r"^(indicator|ml|trend|meanrev|breakout)$")
```

- [ ] **Step 4: Syntax check + commit**

```bash
python -c "import py_compile; py_compile.compile('backend/routers/analysis.py', doraise=True)"
git add backend/routers/analysis.py backend/tests/test_analysis_backtest.py
git commit -m "feat(backtest): accept trend/meanrev/breakout strategies at the API"
```

---

## Task 6: Frontend — strategy type + selector buttons

> **READ FIRST:** `frontend/AGENTS.md`. Read `BacktestPanel.tsx` around the strategy selector (the `onStrategyChange` buttons near the "Strategy + period selectors" comment) and mirror its existing button markup. Read `analysis.ts` for the `BacktestStrategy` type.

**Files:**
- Modify: `frontend/src/lib/api/analysis.ts`
- Modify: `frontend/src/components/analysis/BacktestPanel.tsx`

- [ ] **Step 1: Extend the type** in `frontend/src/lib/api/analysis.ts`:
```typescript
export type BacktestStrategy = "indicator" | "ml" | "trend" | "meanrev" | "breakout";
```

- [ ] **Step 2: Add the three options to the strategy selector** in `BacktestPanel.tsx`. Find the array/list the selector maps over to render the `indicator`/`ml` buttons (it pairs a `value` with a label and calls `onStrategyChange(value)`), and add three entries mirroring the existing shape:
  - `{ value: "trend", label: "Trend" }`
  - `{ value: "meanrev", label: "Mean-Rev" }`
  - `{ value: "breakout", label: "Breakout" }`
  Keep the existing `indicator`/`ml` entries. The per-strategy `strategy_description` already renders from the response, so no other change is needed.

- [ ] **Step 3: Type-check + build**

Run: `cd frontend && npx tsc --noEmit && npx next build --webpack`
Expected: clean; `/dashboard/stocks/[ticker]` route builds. (Local default `npm run build` uses Turbopack which fails on darwin/arm64 — use `--webpack`; CI/Linux is fine.)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/api/analysis.ts frontend/src/components/analysis/BacktestPanel.tsx
git commit -m "feat(backtest): trend/mean-rev/breakout strategy options in the panel"
```

---

## Task 7: Docs

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update the Backtesting "Strategies" section** to list all five strategies with one line each: `indicator` (composite signal), `ml` (RandomForest), `trend` (EMA-50/200 cross), `meanrev` (RSI-14 30/55, dip-buying in uptrends), `breakout` (Donchian 20-day high / 10-day low). Note they all share the v2 engine (uptrend filter, 10%-capped ATR stop, 1:3 target, SELL exit, 1% sizing).

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs(backtest): document the 3 new strategy presets"
```

---

## Task 8: Final verification

- [ ] **Step 1: Python suites**

Run: `python -m pytest tests/test_backtester.py -v && (cd backend && python -m pytest tests/test_analysis_backtest.py -v)`
Expected: all PASS.

- [ ] **Step 2: Frontend gates**

Run: `cd frontend && npx tsc --noEmit && npm run lint`
Expected: clean.

- [ ] **Step 3: Live smoke (optional)**

With the backend (anaconda python) + frontend running, open `/dashboard/stocks/<TICKER>` → Backtest, switch the strategy selector through Trend / Mean-Rev / Breakout, and confirm each loads a result (equity curve, trades with exit reasons, metrics, open-position card when applicable) and the description updates.

- [ ] **Step 4: Final commit (if tweaks remain)**

```bash
git add -A && git commit -m "chore(backtest): phase B verification"
```

---

## Out of Scope (future)
- Per-strategy parameter UI / optimization sweeps.
- More presets (momentum, volatility, pairs).
- Per-strategy exit overrides (all presets share the v2 exits by design).
