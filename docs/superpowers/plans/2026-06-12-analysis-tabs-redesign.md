# Analysis Tabs Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the five stock-detail analysis tabs (Technical, Fundamental, ML Prediction, Confluence, Backtest) with richer rendering and per-tab methodology disclosure, and extend the backtest engine with an ML strategy, buy-&-hold benchmark, trade markers, and expanded stats.

**Architecture:** Backend: `tools/backtester.py` gains a `strategy` parameter ("indicator" | "ml"), a benchmark series, and new stats via a refactor into signal-generation / simulation / stats phases; `/analysis/backtest` exposes the param. Frontend: a shared `MethodologyNote` component backs explainability; each tab's panel component is upgraded in place; the page wires an ML→Backtest handoff via controlled tabs state.

**Tech Stack:** Python (pandas, numpy, scikit-learn, FastAPI), pytest/unittest; Next.js + React, TanStack Query, Recharts, Tailwind, Vitest + Testing Library.

**Spec:** `docs/superpowers/specs/2026-06-12-analysis-tabs-redesign-design.md`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `tools/backtester.py` | Rewrite | Strategy-parameterised walk-forward backtest, benchmark, stats |
| `tests/test_backtester.py` | Create | Backend backtester tests |
| `backend/routers/analysis.py` | Modify | `strategy` query param, cache key, rate limit |
| `frontend/src/lib/api/analysis.ts` | Modify | Types + `useBacktest(strategy)`, ML response fields |
| `frontend/src/components/analysis/MethodologyNote.tsx` | Create | Shared "How this is computed" footnote |
| `frontend/src/components/analysis/SignalCard.tsx` | Modify | Score gauge + price-level rail |
| `frontend/src/components/analysis/IndicatorBreakdown.tsx` | Modify | Diverging contribution bars |
| `frontend/src/components/analysis/FundamentalsPanel.tsx` | Modify | Tone-coded metric cards merged with scoring breakdown |
| `frontend/src/components/analysis/FundamentalsBreakdown.tsx` | Delete | Merged into FundamentalsPanel |
| `frontend/src/components/analysis/MLPredictionCard.tsx` | Modify | Confidence gauge, all features, accuracy context, backtest button |
| `frontend/src/components/analysis/SystemsStrip.tsx` | Create | Cross-system summary strip for Confluence tab |
| `frontend/src/components/analysis/ConfluenceGrid.tsx` | Modify | Tap-friendly legend |
| `frontend/src/components/analysis/BacktestPanel.tsx` | Rewrite | Strategy toggle, benchmark line, markers, 10-stat grid |
| `frontend/src/app/dashboard/stocks/[ticker]/page.tsx` | Modify | Controlled tabs, strategy state, MethodologyNotes, SystemsStrip |
| `frontend/src/test/MethodologyNote.test.tsx` | Create | Component test |
| `frontend/src/test/SystemsStrip.test.tsx` | Create | Component test |
| `frontend/src/test/MLPredictionCard.test.tsx` | Create | Component test |
| `README.md` | Modify | Document backtest strategies |

---

### Task 0: Create feature branch

- [ ] **Step 1: Branch off main**

```bash
cd "/Users/divyanshuagarwal/Downloads/frist workflow"
git checkout main && git pull && git checkout -b feature/analysis-tabs-redesign
```

---

### Task 1: Backtester refactor — benchmark + expanded stats (indicator strategy unchanged)

**Files:**
- Modify: `tools/backtester.py`
- Test: `tests/test_backtester.py` (create)

- [ ] **Step 1: Write failing tests**

Create `tests/test_backtester.py`:

```python
"""
Tests for tools/backtester.py:
- result shape (strategy echo, description, benchmark, new stats)
- stats math on hand-built fixtures
- ML strategy: insufficient-history error, determinism, signal validity
"""

import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, ".")


def synthetic_ohlcv(n: int, seed: int = 42) -> pd.DataFrame:
    """Deterministic random-walk OHLCV with a DatetimeIndex of n business days."""
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0005, 0.015, n)
    close = 100 * np.cumprod(1 + rets)
    dates = pd.bdate_range("2024-01-01", periods=n)
    return pd.DataFrame(
        {
            "Open": close * (1 + rng.normal(0, 0.003, n)),
            "High": close * (1 + np.abs(rng.normal(0, 0.006, n))),
            "Low": close * (1 - np.abs(rng.normal(0, 0.006, n))),
            "Close": close,
            "Volume": rng.integers(1_000_00, 5_000_00, n).astype(float),
        },
        index=dates,
    )


def enriched(n: int, seed: int = 42) -> pd.DataFrame:
    from tools.compute_indicators import compute_all
    return compute_all(synthetic_ohlcv(n, seed))


class IndicatorResultShapeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tools.backtester import run_backtest
        cls.result = run_backtest(enriched(260), strategy="indicator")

    def test_strategy_fields(self):
        self.assertEqual(self.result["strategy"], "indicator")
        self.assertIn("indicator signal", self.result["strategy_description"])
        self.assertIsNone(self.result["error"])

    def test_equity_curve_has_benchmark_starting_at_100(self):
        curve = self.result["equity_curve"]
        self.assertGreater(len(curve), 0)
        self.assertEqual(curve[0]["benchmark"], 100.0)
        for point in curve[:5]:
            self.assertIn("date", point)
            self.assertIn("equity", point)
            self.assertIn("benchmark", point)

    def test_new_stats_present(self):
        stats = self.result["stats"]
        for key in (
            "sharpe_ratio", "profit_factor", "exposure_pct",
            "avg_hold_days", "buy_hold_return_pct",
        ):
            self.assertIn(key, stats)

    def test_buy_hold_matches_benchmark_end(self):
        curve = self.result["equity_curve"]
        expected = curve[-1]["benchmark"] - 100.0
        self.assertAlmostEqual(
            self.result["stats"]["buy_hold_return_pct"], expected, places=1
        )


class StatsMathTest(unittest.TestCase):
    def test_compute_stats_on_fixture(self):
        from tools.backtester import _compute_stats
        trades = [
            {"date_entry": "2024-01-01", "date_exit": "2024-01-11",
             "entry_price": 100.0, "exit_price": 110.0, "pnl_pct": 10.0},
            {"date_entry": "2024-02-01", "date_exit": "2024-02-06",
             "entry_price": 100.0, "exit_price": 95.0, "pnl_pct": -5.0},
        ]
        equity_curve = [
            {"date": "2024-01-01", "equity": 100.0, "benchmark": 100.0},
            {"date": "2024-01-11", "equity": 110.0, "benchmark": 105.0},
            {"date": "2024-02-06", "equity": 104.5, "benchmark": 102.0},
        ]
        stats = _compute_stats(
            trades=trades, equity_curve=equity_curve,
            final_equity=104.5, bars_long=10, n_signal_bars=20,
            buy_hold_return_pct=2.0,
        )
        self.assertEqual(stats["num_trades"], 2)
        self.assertEqual(stats["win_rate"], 0.5)
        self.assertAlmostEqual(stats["total_return_pct"], 4.5)
        self.assertAlmostEqual(stats["profit_factor"], 2.0)   # 10 / 5
        self.assertAlmostEqual(stats["exposure_pct"], 50.0)   # 10 / 20
        self.assertAlmostEqual(stats["avg_hold_days"], 7.5)   # (10 + 5) / 2
        self.assertAlmostEqual(stats["buy_hold_return_pct"], 2.0)

    def test_profit_factor_null_when_no_losses(self):
        from tools.backtester import _compute_stats
        trades = [{"date_entry": "2024-01-01", "date_exit": "2024-01-08",
                   "entry_price": 100.0, "exit_price": 108.0, "pnl_pct": 8.0}]
        stats = _compute_stats(
            trades=trades,
            equity_curve=[{"date": "2024-01-01", "equity": 100.0, "benchmark": 100.0},
                          {"date": "2024-01-08", "equity": 108.0, "benchmark": 101.0}],
            final_equity=108.0, bars_long=5, n_signal_bars=10,
            buy_hold_return_pct=1.0,
        )
        self.assertIsNone(stats["profit_factor"])

    def test_empty_trades_stats(self):
        from tools.backtester import _compute_stats
        stats = _compute_stats(
            trades=[], equity_curve=[], final_equity=100.0,
            bars_long=0, n_signal_bars=0, buy_hold_return_pct=0.0,
        )
        self.assertEqual(stats["num_trades"], 0)
        self.assertEqual(stats["win_rate"], 0.0)
        self.assertEqual(stats["sharpe_ratio"], 0.0)
        self.assertIsNone(stats["profit_factor"])


class ShortHistoryTest(unittest.TestCase):
    def test_indicator_short_df_returns_empty_shape(self):
        from tools.backtester import run_backtest
        result = run_backtest(enriched(30), strategy="indicator")
        self.assertEqual(result["trades"], [])
        self.assertEqual(result["stats"]["num_trades"], 0)
        self.assertEqual(result["strategy"], "indicator")

    def test_unknown_strategy_raises(self):
        from tools.backtester import run_backtest
        with self.assertRaises(ValueError):
            run_backtest(enriched(260), strategy="quantum")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd "/Users/divyanshuagarwal/Downloads/frist workflow" && python -m pytest tests/test_backtester.py -v
```

Expected: FAIL — `run_backtest()` doesn't accept `strategy`, `_compute_stats` doesn't exist, equity points lack `benchmark`.

- [ ] **Step 3: Rewrite `tools/backtester.py`**

Replace the entire file with:

```python
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
        "strategy_description": STRATEGY_DESCRIPTIONS[strategy],
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
            p_up = float(classes[0])  # degenerate single-class training window
        else:
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
    losses = [t for t in trades if t["pnl_pct"] <= 0]

    eq = np.array([p["equity"] for p in equity_curve], dtype=float)
    if len(eq) >= 3 and np.std(np.diff(eq) / eq[:-1]) > 0:
        rets = np.diff(eq) / eq[:-1]
        sharpe = round(float(np.mean(rets) / np.std(rets) * np.sqrt(252)), 2)
    else:
        sharpe = 0.0

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
```

- [ ] **Step 4: Syntax-check and run the Task 1 tests**

```bash
cd "/Users/divyanshuagarwal/Downloads/frist workflow"
python -c "import py_compile; py_compile.compile('tools/backtester.py', doraise=True)"
python -m pytest tests/test_backtester.py -v
```

Expected: all Task 1 tests PASS (ML tests come in Task 2).

- [ ] **Step 5: Run the full existing backend suite to catch regressions**

```bash
python -m pytest tests/ -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/backtester.py tests/test_backtester.py
git commit -m "feat(backtest): benchmark series, expanded stats, strategy plumbing"
```

---

### Task 2: ML strategy tests

**Files:**
- Modify: `tests/test_backtester.py` (append)

The `_ml_signals` implementation already landed in Task 1's rewrite; this task locks its behaviour with tests.

- [ ] **Step 1: Append ML tests to `tests/test_backtester.py`**

```python
class MLStrategyTest(unittest.TestCase):
    def test_insufficient_history_returns_error(self):
        from tools.backtester import ML_WARMUP, RETRAIN_EVERY, run_backtest
        n_short = ML_WARMUP + RETRAIN_EVERY - 1
        result = run_backtest(enriched(n_short), strategy="ml")
        self.assertIsNotNone(result["error"])
        self.assertIn("ML backtest", result["error"])
        self.assertEqual(result["trades"], [])
        self.assertEqual(result["strategy"], "ml")

    def test_ml_backtest_runs_and_is_deterministic(self):
        from tools.backtester import run_backtest
        df = enriched(300)
        r1 = run_backtest(df, strategy="ml")
        r2 = run_backtest(df, strategy="ml")
        self.assertIsNone(r1["error"])
        self.assertEqual(r1["strategy"], "ml")
        self.assertIn("RandomForest", r1["strategy_description"])
        self.assertGreater(len(r1["equity_curve"]), 0)
        self.assertEqual(r1["trades"], r2["trades"])              # random_state=42
        self.assertEqual(r1["equity_curve"], r2["equity_curve"])

    def test_ml_signals_cover_all_post_warmup_bars(self):
        from tools.backtester import ML_WARMUP, _ml_signals
        df = enriched(300)
        signals = _ml_signals(df, ML_WARMUP)
        self.assertEqual(len(signals), len(df) - ML_WARMUP)
        self.assertTrue(set(signals) <= {"BUY", "SELL", "HOLD"})
```

- [ ] **Step 2: Run the tests**

```bash
python -m pytest tests/test_backtester.py -v
```

Expected: PASS. (The ML test trains ~9 forests on 300 rows; expect a few seconds.)

- [ ] **Step 3: Commit**

```bash
git add tests/test_backtester.py
git commit -m "test(backtest): ML walk-forward strategy coverage"
```

---

### Task 3: Backtest endpoint — strategy param

**Files:**
- Modify: `backend/routers/analysis.py:170-195`

- [ ] **Step 1: Update the endpoint**

In `backend/routers/analysis.py`, add below the `_PERIOD` definition (line 21):

```python
_STRATEGY = Query("indicator", pattern=r"^(indicator|ml)$")
```

Replace the `get_backtest` function (lines 170–195) with:

```python
@router.get("/analysis/backtest")
@limiter.limit("10/minute")
async def get_backtest(
    request: Request,
    ticker: str = _TICKER,
    period: str = _PERIOD,
    strategy: str = _STRATEGY,
    user: dict = Depends(verify_supabase_jwt),
):
    """Walk-forward backtest on daily OHLCV.

    strategy=indicator trades the composite technical signal;
    strategy=ml trades a RandomForest next-day direction model
    retrained monthly on a walk-forward basis.
    """
    cache_key = f"backtest:{ticker}:{period}:{strategy}"

    try:
        from services.daily_data import get_daily_df
        from tools.backtester import run_backtest
        from tools.compute_indicators import compute_all

        async def _run():
            df = await get_daily_df(ticker, period)
            return await asyncio.to_thread(
                lambda: run_backtest(compute_all(df.copy()), strategy=strategy)
            )

        result = await cached(cache_key, ttl=adaptive_ttl(21600), fn=_run)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.exception("Backtest failed for %s: %s", ticker, e)
        raise HTTPException(status_code=503, detail=f"Backtest failed: {e}")

    return {"ticker": ticker, **result}
```

Note: `request: Request` is required by `@limiter.limit` (same pattern as `get_ml_prediction`).

- [ ] **Step 2: Syntax-check and lint**

```bash
python -c "import py_compile; py_compile.compile('backend/routers/analysis.py', doraise=True)"
ruff check backend/routers/analysis.py tools/backtester.py
```

Expected: clean.

- [ ] **Step 3: Run the backend suite**

```bash
python -m pytest tests/ -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/routers/analysis.py
git commit -m "feat(api): strategy param + rate limit on /analysis/backtest"
```

---

### Task 4: Frontend API client — types and strategy param

**Files:**
- Modify: `frontend/src/lib/api/analysis.ts`

- [ ] **Step 1: Update types and hook**

In `frontend/src/lib/api/analysis.ts`, replace the `MLResponse` interface with (adds fields the backend already returns):

```ts
export interface MLResponse {
  ticker: string;
  direction: "UP" | "DOWN" | null;
  probability: number;
  accuracy: number;
  feature_importance: Record<string, number>;
  train_samples?: number;
  test_samples?: number;
  error: string | null;
}
```

Replace `BacktestStats`, `BacktestResponse`, and `useBacktest` with:

```ts
export interface BacktestStats {
  num_trades: number;
  win_rate: number;
  total_return_pct: number;
  avg_gain_pct: number;
  avg_loss_pct: number;
  max_drawdown_pct: number;
  sharpe_ratio: number;
  profit_factor: number | null;
  exposure_pct: number;
  avg_hold_days: number;
  buy_hold_return_pct: number;
}

export type BacktestStrategy = "indicator" | "ml";

export interface BacktestResponse {
  ticker: string;
  trades: BacktestTrade[];
  equity_curve: Array<{ date: string; equity: number; benchmark: number }>;
  stats: BacktestStats;
  strategy: BacktestStrategy;
  strategy_description: string;
  error: string | null;
}

export function useBacktest(
  ticker: string,
  period = "1y",
  strategy: BacktestStrategy = "indicator",
  enabled = true,
) {
  return useQuery({
    queryKey: ["backtest", ticker, period, strategy],
    queryFn: () =>
      apiFetch<BacktestResponse>("/api/v1/analysis/backtest", { ticker, period, strategy }),
    staleTime: 6 * 60 * 60 * 1000,
    enabled: !!ticker && enabled,
  });
}
```

- [ ] **Step 2: Type-check (expect one known break)**

```bash
cd "/Users/divyanshuagarwal/Downloads/frist workflow/frontend" && npx tsc --noEmit
```

Expected: errors only in `BacktestPanel.tsx` (call signature) — fixed in Task 9. No other errors.

- [ ] **Step 3: Commit**

```bash
git add src/lib/api/analysis.ts
git commit -m "feat(frontend): backtest strategy param + expanded response types"
```

---

### Task 5: MethodologyNote shared component

**Files:**
- Create: `frontend/src/components/analysis/MethodologyNote.tsx`
- Test: `frontend/src/test/MethodologyNote.test.tsx`

- [ ] **Step 1: Write failing test**

Create `frontend/src/test/MethodologyNote.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MethodologyNote } from "@/components/analysis/MethodologyNote";

describe("MethodologyNote", () => {
  it("renders the default summary title", () => {
    render(<MethodologyNote>Some explanation</MethodologyNote>);
    expect(screen.getByText("How this is computed")).toBeInTheDocument();
  });

  it("renders custom title and body content", () => {
    render(<MethodologyNote title="Backtest method">Walk-forward, no look-ahead.</MethodologyNote>);
    expect(screen.getByText("Backtest method")).toBeInTheDocument();
    expect(screen.getByText("Walk-forward, no look-ahead.")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "/Users/divyanshuagarwal/Downloads/frist workflow/frontend" && npx vitest run src/test/MethodologyNote.test.tsx
```

Expected: FAIL — module not found.

- [ ] **Step 3: Create the component**

Create `frontend/src/components/analysis/MethodologyNote.tsx`:

```tsx
import { Info } from "lucide-react";

interface Props {
  title?: string;
  children: React.ReactNode;
}

export function MethodologyNote({ title = "How this is computed", children }: Props) {
  return (
    <details className="bg-muted/30 border border-border rounded-xl px-4 py-3 text-xs text-muted-foreground">
      <summary className="cursor-pointer select-none font-medium text-foreground/70 hover:text-foreground transition-colors inline-flex items-center gap-1.5">
        <Info size={12} className="shrink-0" />
        {title}
      </summary>
      <div className="mt-2 leading-relaxed space-y-1.5">{children}</div>
    </details>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
npx vitest run src/test/MethodologyNote.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/components/analysis/MethodologyNote.tsx src/test/MethodologyNote.test.tsx
git commit -m "feat(frontend): shared MethodologyNote disclosure component"
```

---

### Task 6: Technical tab — score gauge, price rail, diverging indicator bars

**Files:**
- Modify: `frontend/src/components/analysis/SignalCard.tsx`
- Modify: `frontend/src/components/analysis/IndicatorBreakdown.tsx`
- Test: `frontend/src/test/SignalCard.test.tsx` (existing — must keep passing)

- [ ] **Step 1: Rewrite `SignalCard.tsx`**

Replace the file contents with:

```tsx
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { SignalResponse } from "@/lib/api/market";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface Props { data: SignalResponse }

const signalConfig = {
  BUY:  { color: "text-buy",  bg: "bg-buy/10",  border: "border-buy/20",  icon: TrendingUp,   label: "BUY" },
  SELL: { color: "text-sell", bg: "bg-sell/10", border: "border-sell/20", icon: TrendingDown, label: "SELL" },
  HOLD: { color: "text-hold", bg: "bg-hold/10", border: "border-hold/20", icon: Minus,        label: "HOLD" },
};

function ScoreGauge({ score }: { score: number }) {
  return (
    <div>
      <div className="relative h-2.5 rounded-full overflow-visible flex">
        <div className="h-full bg-sell/25 rounded-l-full" style={{ width: "40%" }} />
        <div className="h-full bg-hold/25" style={{ width: "20%" }} />
        <div className="h-full bg-buy/25 rounded-r-full" style={{ width: "40%" }} />
        <div
          className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-3.5 h-3.5 rounded-full bg-foreground border-2 border-card shadow"
          style={{ left: `${Math.min(100, Math.max(0, score))}%` }}
          aria-label={`Score ${score} of 100`}
        />
      </div>
      <div className="flex justify-between text-[10px] text-muted-foreground mt-1.5">
        <span>SELL &lt; 40</span>
        <span>HOLD</span>
        <span>BUY &gt; 60</span>
      </div>
    </div>
  );
}

function PriceLevelRail({ entry, stopLoss, target }: { entry: number; stopLoss: number; target: number }) {
  const lo = Math.min(entry, stopLoss, target);
  const hi = Math.max(entry, stopLoss, target);
  const span = hi - lo || 1;
  const pos = (v: number) => ((v - lo) / span) * 100;
  const levels = [
    { label: "Stop Loss", value: stopLoss, dot: "bg-sell", text: "text-sell" },
    { label: "Entry", value: entry, dot: "bg-foreground", text: "text-foreground" },
    { label: "Target", value: target, dot: "bg-buy", text: "text-buy" },
  ];
  return (
    <div className="pt-1">
      <div className="relative h-1.5 bg-muted rounded-full mx-2">
        {levels.map((l) => (
          <div
            key={l.label}
            className={cn("absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-3 h-3 rounded-full border-2 border-card shadow", l.dot)}
            style={{ left: `${pos(l.value)}%` }}
          />
        ))}
      </div>
      <div className="relative h-9 mx-2 mt-1.5">
        {levels.map((l) => (
          <div
            key={l.label}
            className="absolute -translate-x-1/2 text-center"
            style={{ left: `${Math.min(92, Math.max(8, pos(l.value)))}%` }}
          >
            <p className="text-[10px] text-muted-foreground whitespace-nowrap">{l.label}</p>
            <p className={cn("font-mono text-xs font-semibold tabular-nums whitespace-nowrap", l.text)}>
              &#8377;{l.value.toFixed(2)}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function SignalCard({ data }: Props) {
  const cfg = signalConfig[data.signal];
  const Icon = cfg.icon;

  return (
    <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Signal</p>
          <Badge className={cn("text-base px-4 py-1.5 rounded-full font-bold border", cfg.bg, cfg.color, cfg.border)}>
            <Icon size={14} className="mr-1.5" />
            {cfg.label}
          </Badge>
        </div>
        <div className="text-right">
          <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Confidence</p>
          <p className={cn("text-3xl font-bold font-mono tabular-nums", cfg.color)}>{data.confidence}%</p>
        </div>
      </div>

      <ScoreGauge score={data.confidence} />

      <PriceLevelRail entry={data.last_price} stopLoss={data.stop_loss} target={data.target} />
    </div>
  );
}
```

- [ ] **Step 2: Run existing SignalCard tests**

```bash
npx vitest run src/test/SignalCard.test.tsx
```

Expected: PASS (labels "Entry", "Stop Loss", "Target", signal text and "72%" all still rendered).

- [ ] **Step 3: Rewrite `IndicatorBreakdown.tsx` with diverging bars**

Replace the file contents with:

```tsx
import { cn } from "@/lib/utils";
import type { SignalResponse } from "@/lib/api/market";

interface Props { components: SignalResponse["components"] }

export function IndicatorBreakdown({ components }: Props) {
  const entries = Object.entries(components);
  // Scale bars to the largest absolute contribution so they stay comparable.
  const maxAbs = Math.max(1, ...entries.map(([, d]) => Math.abs(d.points)));

  return (
    <div className="bg-card border border-border rounded-2xl p-6">
      <h3 className="text-sm font-semibold mb-4 text-muted-foreground uppercase tracking-wider">
        Technical Indicators
      </h3>
      <div className="space-y-3">
        {entries.map(([name, data]) => {
          const widthPct = (Math.abs(data.points) / maxAbs) * 50;
          return (
            <div key={name}>
              <div className="flex items-baseline justify-between gap-2 mb-1">
                <div className="flex items-baseline gap-2 min-w-0">
                  <p className="text-sm font-medium">{name}</p>
                  {data.value !== undefined && data.value !== null && data.value !== "N/A" && (
                    <p className="text-[11px] font-mono text-muted-foreground truncate">
                      {String(data.value)}
                    </p>
                  )}
                </div>
                <span
                  className={cn(
                    "text-xs font-bold font-mono shrink-0",
                    data.points > 0 ? "text-buy" : data.points < 0 ? "text-sell" : "text-muted-foreground",
                  )}
                >
                  {data.points > 0 ? `+${data.points}` : data.points}
                </span>
              </div>
              {/* Diverging bar: bearish extends left of centre, bullish right */}
              <div className="relative h-1.5 bg-muted rounded-full">
                <div className="absolute inset-y-0 left-1/2 w-px bg-border" />
                {data.points !== 0 && (
                  <div
                    className={cn(
                      "absolute inset-y-0 rounded-full",
                      data.points > 0 ? "left-1/2 bg-buy" : "right-1/2 bg-sell",
                    )}
                    style={{ width: `${widthPct}%` }}
                  />
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-1 truncate">{data.signal}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Verify types and full frontend test suite**

```bash
npx tsc --noEmit ; npx vitest run
```

Expected: tsc errors only in `BacktestPanel.tsx` (known, Task 9); vitest PASS.

- [ ] **Step 5: Commit**

```bash
git add src/components/analysis/SignalCard.tsx src/components/analysis/IndicatorBreakdown.tsx
git commit -m "feat(frontend): score gauge, price rail, diverging indicator bars"
```

---

### Task 7: Fundamental tab — tone-coded metric cards merged with scoring

**Files:**
- Modify: `frontend/src/components/analysis/FundamentalsPanel.tsx`
- Delete: `frontend/src/components/analysis/FundamentalsBreakdown.tsx`
- Modify: `frontend/src/app/dashboard/stocks/[ticker]/page.tsx` (imports + usage; full page edit lands in Task 11 — here only remove the `FundamentalsBreakdown` import/usage and pass `breakdown`)

- [ ] **Step 1: Rewrite `FundamentalsPanel.tsx`**

Replace the file contents with:

```tsx
import { cn } from "@/lib/utils";
import type { FundamentalsBreakdownItem } from "@/lib/api/analysis";

interface Props {
  data: Record<string, number | string | null>;
  ticker: string;
  breakdown?: Record<string, FundamentalsBreakdownItem>;
}

function fmt(val: number | string | null, type: "num" | "pct" | "cr" | "str"): string {
  if (val === null || val === undefined) return "—";
  if (type === "str") return String(val);
  const n = Number(val);
  if (isNaN(n)) return "—";
  if (type === "pct") return `${(n * 100).toFixed(1)}%`;
  if (type === "cr") {
    if (n >= 1e7) return `₹${(n / 1e7).toFixed(2)}Cr`;
    return `₹${n.toFixed(2)}`;
  }
  return n.toFixed(2);
}

// Metric label → score_fundamentals breakdown key (tools/fetch_fundamentals.py)
const BREAKDOWN_KEY: Record<string, string> = {
  "P/E (TTM)": "PE Ratio",
  "ROE": "ROE",
  "D/E Ratio": "Debt / Equity",
  "Revenue Growth": "Revenue Growth",
};

function tone(item?: FundamentalsBreakdownItem) {
  if (!item || item.max <= 0) return { card: "", bar: "bg-muted" };
  const pct = (item.points / item.max) * 100;
  if (pct >= 66) return { card: "border-buy/30 bg-buy/5", bar: "bg-buy" };
  if (pct >= 33) return { card: "border-hold/30 bg-hold/5", bar: "bg-hold" };
  return { card: "border-sell/30 bg-sell/5", bar: "bg-sell" };
}

export function FundamentalsPanel({ data, breakdown = {} }: Props) {
  const metrics = [
    { label: "P/E (TTM)", value: fmt(data.pe_trailing, "num") },
    { label: "P/E (Fwd)", value: fmt(data.pe_forward, "num") },
    { label: "P/B Ratio", value: fmt(data.pb_ratio, "num") },
    { label: "ROE", value: fmt(data.roe, "pct") },
    { label: "ROA", value: fmt(data.roa, "pct") },
    { label: "D/E Ratio", value: fmt(data.debt_to_equity, "num") },
    { label: "Revenue Growth", value: fmt(data.revenue_growth, "pct") },
    { label: "Profit Growth", value: fmt(data.profit_growth, "pct") },
    { label: "Market Cap", value: fmt(data.market_cap, "cr") },
    { label: "Div Yield", value: fmt(data.dividend_yield, "pct") },
    { label: "Beta", value: fmt(data.beta, "num") },
    { label: "52W High", value: data.high_52w != null ? `₹${Number(data.high_52w).toFixed(2)}` : "—" },
    { label: "52W Low", value: data.low_52w != null ? `₹${Number(data.low_52w).toFixed(2)}` : "—" },
    { label: "52W Change", value: fmt(data.week52_change, "pct") },
  ];

  // Scoring components without a metric card (e.g. Net Margin, Analyst View)
  const mappedKeys = new Set(Object.values(BREAKDOWN_KEY));
  const drivers = Object.entries(breakdown).filter(([key]) => !mappedKeys.has(key));

  return (
    <div className="bg-card border border-border rounded-2xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Fundamentals</h3>
        {data.sector && <span className="text-xs text-muted-foreground">{String(data.sector)}</span>}
      </div>
      {data.name && <p className="text-base font-semibold mb-4">{String(data.name)}</p>}

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {metrics.map((m) => {
          const item = breakdown[BREAKDOWN_KEY[m.label]];
          const t = tone(item);
          return (
            <div key={m.label} className={cn("rounded-xl p-3 border border-transparent bg-muted/40", t.card)}>
              <p className="text-xs text-muted-foreground mb-0.5">{m.label}</p>
              <p className="text-sm font-semibold font-mono tabular-nums">{m.value}</p>
              {item && (
                <p className="text-[10px] text-muted-foreground mt-1 leading-snug">{item.label}</p>
              )}
            </div>
          );
        })}
      </div>

      {drivers.length > 0 && (
        <div className="mt-5 pt-4 border-t border-border/50">
          <p className="text-xs text-muted-foreground uppercase tracking-wider font-medium mb-3">
            Other Score Drivers
          </p>
          <div className="space-y-3">
            {drivers.map(([name, item]) => {
              const pct = item.max > 0 ? Math.max(0, Math.min(100, (item.points / item.max) * 100)) : 0;
              const t = tone(item);
              return (
                <div key={name}>
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-sm font-medium">{name}</p>
                    <p className="text-xs font-mono text-muted-foreground">{item.points}/{item.max}</p>
                  </div>
                  <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                    <div className={cn("h-full rounded-full transition-all", t.bar)} style={{ width: `${pct}%` }} />
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">{item.label}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Delete `FundamentalsBreakdown.tsx` and update the page**

```bash
git rm src/components/analysis/FundamentalsBreakdown.tsx
```

In `frontend/src/app/dashboard/stocks/[ticker]/page.tsx`:
- Remove the import line: `import { FundamentalsBreakdown } from "@/components/analysis/FundamentalsBreakdown";`
- Replace the Fundamental tab's panel usage:

```tsx
              <FundamentalsPanel
                data={fundamentals.fundamentals}
                ticker={ticker}
                breakdown={fundamentals.breakdown}
              />
```

and delete the block:

```tsx
              {fundamentals.breakdown && (
                <FundamentalsBreakdown breakdown={fundamentals.breakdown} />
              )}
```

- [ ] **Step 3: Verify**

```bash
npx tsc --noEmit ; npx vitest run
```

Expected: tsc errors only in `BacktestPanel.tsx` (known); vitest PASS.

- [ ] **Step 4: Commit**

```bash
git add -A src/components/analysis src/app/dashboard/stocks
git commit -m "feat(frontend): merge fundamentals scoring into tone-coded metric cards"
```

---

### Task 8: ML Prediction tab — gauge, all features, accuracy context, backtest handoff

**Files:**
- Modify: `frontend/src/components/analysis/MLPredictionCard.tsx`
- Test: `frontend/src/test/MLPredictionCard.test.tsx` (create)

- [ ] **Step 1: Write failing test**

Create `frontend/src/test/MLPredictionCard.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MLPredictionCard, FEATURE_LABELS } from "@/components/analysis/MLPredictionCard";
import type { MLResponse } from "@/lib/api/analysis";

const baseML: MLResponse = {
  ticker: "RELIANCE.NS",
  direction: "UP",
  probability: 0.62,
  accuracy: 0.55,
  feature_importance: { rsi: 0.2, ema200_dist: 0.15, ret_5d: 0.1 },
  train_samples: 180,
  test_samples: 45,
  error: null,
};

describe("MLPredictionCard", () => {
  it("renders direction, probability and accuracy context", () => {
    render(<MLPredictionCard data={baseML} onBacktestModel={() => {}} />);
    expect(screen.getByText("UP")).toBeInTheDocument();
    expect(screen.getByText("62%")).toBeInTheDocument();
    expect(screen.getByText(/55% accuracy on the last 45 sessions/)).toBeInTheDocument();
  });

  it("maps feature keys to readable labels", () => {
    expect(FEATURE_LABELS.ema200_dist).toBe("Distance from EMA 200");
    render(<MLPredictionCard data={baseML} onBacktestModel={() => {}} />);
    expect(screen.getByText("Distance from EMA 200")).toBeInTheDocument();
  });

  it("fires onBacktestModel when the button is clicked", () => {
    const onBacktest = vi.fn();
    render(<MLPredictionCard data={baseML} onBacktestModel={onBacktest} />);
    fireEvent.click(screen.getByText(/Backtest this model/));
    expect(onBacktest).toHaveBeenCalledOnce();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
npx vitest run src/test/MLPredictionCard.test.tsx
```

Expected: FAIL — `FEATURE_LABELS` not exported, `onBacktestModel` prop unknown.

- [ ] **Step 3: Rewrite `MLPredictionCard.tsx`**

Replace the file contents with:

```tsx
import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, FlaskConical } from "lucide-react";
import type { MLResponse } from "@/lib/api/analysis";

interface Props {
  data: MLResponse;
  onBacktestModel: () => void;
}

export const FEATURE_LABELS: Record<string, string> = {
  rsi: "RSI (14)",
  macd_hist: "MACD histogram",
  bb_pct: "Bollinger %B",
  ema9_dist: "Distance from EMA 9",
  ema21_dist: "Distance from EMA 21",
  ema50_dist: "Distance from EMA 50",
  ema200_dist: "Distance from EMA 200",
  atr_pct: "ATR % of price",
  vol_change: "Volume vs 10-day avg",
  ret_1d: "1-day return",
  ret_5d: "5-day return",
  obv_slope: "OBV slope",
};

export function MLPredictionCard({ data, onBacktestModel }: Props) {
  const isUp = data.direction === "UP";
  const pct = Math.round((data.probability ?? 0) * 100);
  const accuracy = Math.round((data.accuracy ?? 0) * 100);
  const features = Object.entries(data.feature_importance ?? {}).sort((a, b) => b[1] - a[1]);
  const maxImp = Math.max(0.0001, ...features.map(([, imp]) => imp));

  return (
    <div className="bg-card border border-border rounded-2xl p-6 space-y-5">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">ML Prediction</h3>
        <button
          onClick={onBacktestModel}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline"
        >
          <FlaskConical size={13} />
          Backtest this model &rarr;
        </button>
      </div>

      <div className="flex items-center gap-4">
        <div className={cn(
          "w-14 h-14 rounded-2xl flex items-center justify-center",
          isUp ? "bg-buy/10" : "bg-sell/10"
        )}>
          {isUp
            ? <TrendingUp size={24} className="text-buy" />
            : <TrendingDown size={24} className="text-sell" />}
        </div>
        <div>
          <p className={cn("text-2xl font-bold font-display", isUp ? "text-buy" : "text-sell")}>
            {data.direction ?? "N/A"}
          </p>
          <p className="text-xs text-muted-foreground">Next day direction</p>
        </div>
        <div className="ml-auto text-right">
          <p className="text-2xl font-bold font-mono tabular-nums">{pct}%</p>
          <p className="text-xs text-muted-foreground">Probability</p>
        </div>
      </div>

      {/* Confidence gauge with 50% coin-flip anchor */}
      <div>
        <div className="relative h-2 bg-muted rounded-full">
          <div
            className={cn("absolute inset-y-0 left-0 rounded-full transition-all duration-700", isUp ? "bg-buy" : "bg-sell")}
            style={{ width: `${pct}%` }}
          />
          <div className="absolute inset-y-[-3px] left-1/2 w-px bg-foreground/40" />
        </div>
        <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
          <span>0%</span>
          <span>50% = coin flip</span>
          <span>100%</span>
        </div>
      </div>

      {/* Honest accuracy context */}
      <div className="bg-muted/40 rounded-xl px-3 py-2.5 text-xs text-muted-foreground leading-relaxed">
        <span className="font-semibold text-foreground/80">{accuracy}% accuracy on the last {data.test_samples ?? "?"} sessions</span>{" "}
        (time-ordered hold-out; trained on {data.train_samples ?? "?"} sessions). Next-day direction is
        near-random &mdash; treat accuracy below 55% as noise.
      </div>

      {/* All feature importances */}
      {features.length > 0 && (
        <div>
          <p className="text-xs text-muted-foreground mb-2">Feature Importance</p>
          <div className="space-y-1.5">
            {features.map(([feat, imp]) => (
              <div key={feat} className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground w-40 truncate">
                  {FEATURE_LABELS[feat] ?? feat}
                </span>
                <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary/60 rounded-full"
                    style={{ width: `${Math.round((imp / maxImp) * 100)}%` }}
                  />
                </div>
                <span className="text-xs font-mono text-muted-foreground w-10 text-right">
                  {(imp * 100).toFixed(1)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run tests**

```bash
npx vitest run src/test/MLPredictionCard.test.tsx
```

Expected: PASS. (The page passes `onBacktestModel` in Task 11; tsc will flag the missing prop at the page call-site until then — acceptable mid-branch.)

- [ ] **Step 5: Commit**

```bash
git add src/components/analysis/MLPredictionCard.tsx src/test/MLPredictionCard.test.tsx
git commit -m "feat(frontend): ML card gauge, full features, accuracy context, backtest handoff"
```

---

### Task 9: Backtest tab — strategy toggle, benchmark, markers, 10-stat grid

**Files:**
- Rewrite: `frontend/src/components/analysis/BacktestPanel.tsx`

- [ ] **Step 1: Rewrite `BacktestPanel.tsx`**

Replace the file contents with:

```tsx
"use client";
import { useState } from "react";
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceDot,
} from "recharts";
import { AlertCircle, Cpu, Activity } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useBacktest, type BacktestStrategy } from "@/lib/api/analysis";
import { MethodologyNote } from "@/components/analysis/MethodologyNote";

const PERIODS = ["6mo", "1y", "2y"] as const;
type Period = typeof PERIODS[number];
const PERIOD_LABELS: Record<Period, string> = { "6mo": "6M", "1y": "1Y", "2y": "2Y" };

const STRATEGIES: Array<{ value: BacktestStrategy; label: string; icon: typeof Activity }> = [
  { value: "indicator", label: "Indicator", icon: Activity },
  { value: "ml", label: "ML Model", icon: Cpu },
];

function EquityTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ dataKey: string; value: number; payload: { date: string } }>;
}) {
  if (!active || !payload?.length) return null;
  const { date } = payload[0].payload;
  const equity = payload.find((p) => p.dataKey === "equity")?.value;
  const benchmark = payload.find((p) => p.dataKey === "benchmark")?.value;
  return (
    <div className="bg-card border border-border rounded-xl px-3 py-2 text-xs shadow-md space-y-0.5">
      <div className="text-muted-foreground">{date}</div>
      {equity != null && (
        <div className={equity - 100 >= 0 ? "text-buy font-semibold" : "text-sell font-semibold"}>
          Strategy: {equity - 100 >= 0 ? "+" : ""}{(equity - 100).toFixed(1)}%
        </div>
      )}
      {benchmark != null && (
        <div className="text-muted-foreground">
          Buy &amp; hold: {benchmark - 100 >= 0 ? "+" : ""}{(benchmark - 100).toFixed(1)}%
        </div>
      )}
    </div>
  );
}

interface Props {
  ticker: string;
  enabled?: boolean;
  strategy: BacktestStrategy;
  onStrategyChange: (s: BacktestStrategy) => void;
}

export function BacktestPanel({ ticker, enabled = true, strategy, onStrategyChange }: Props) {
  const [period, setPeriod] = useState<Period>("1y");
  const { data, isLoading, isError } = useBacktest(ticker, period, strategy, enabled);

  const eqByDate = new Map((data?.equity_curve ?? []).map((p) => [p.date, p.equity]));

  const fmtPct = (v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`;

  const statCards = data
    ? [
        {
          label: "Total Return",
          value: fmtPct(data.stats.total_return_pct),
          sub: `Buy & hold ${fmtPct(data.stats.buy_hold_return_pct)}`,
          color: data.stats.total_return_pct >= 0 ? "text-buy" : "text-sell",
        },
        {
          label: "Win Rate",
          value: `${(data.stats.win_rate * 100).toFixed(0)}%`,
          sub: "Winning round trips",
          color: "text-foreground",
        },
        {
          label: "# Trades",
          value: String(data.stats.num_trades),
          sub: "Round trips",
          color: "text-foreground",
        },
        {
          label: "Avg Gain",
          value: `+${data.stats.avg_gain_pct.toFixed(1)}%`,
          sub: "Mean winning trade",
          color: "text-buy",
        },
        {
          label: "Avg Loss",
          value: `${data.stats.avg_loss_pct.toFixed(1)}%`,
          sub: "Mean losing trade",
          color: "text-sell",
        },
        {
          label: "Max Drawdown",
          value: `${data.stats.max_drawdown_pct.toFixed(1)}%`,
          sub: "Peak-to-trough equity",
          color: "text-sell",
        },
        {
          label: "Sharpe",
          value: data.stats.sharpe_ratio.toFixed(2),
          sub: "Annualised, daily returns",
          color: "text-foreground",
        },
        {
          label: "Profit Factor",
          value: data.stats.profit_factor != null ? data.stats.profit_factor.toFixed(2) : "∞",
          sub: "Gross gains ÷ losses",
          color: "text-foreground",
        },
        {
          label: "Exposure",
          value: `${data.stats.exposure_pct.toFixed(0)}%`,
          sub: "Time in market",
          color: "text-foreground",
        },
        {
          label: "Avg Hold",
          value: `${data.stats.avg_hold_days.toFixed(0)}d`,
          sub: "Calendar days per trade",
          color: "text-foreground",
        },
      ]
    : [];

  return (
    <div className="space-y-4">
      {/* Strategy + period selectors */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex gap-1.5">
          {STRATEGIES.map(({ value, label, icon: Icon }) => (
            <button
              key={value}
              onClick={() => onStrategyChange(value)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors ${
                strategy === value
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted/60 text-muted-foreground hover:text-foreground"
              }`}
            >
              <Icon size={13} />
              {label}
            </button>
          ))}
        </div>
        <div className="flex gap-1.5">
          {PERIODS.map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors ${
                period === p
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted/60 text-muted-foreground hover:text-foreground"
              }`}
            >
              {PERIOD_LABELS[p]}
            </button>
          ))}
        </div>
      </div>

      {/* What is this trading? */}
      {data?.strategy_description && (
        <p className="text-xs text-muted-foreground bg-muted/30 border border-border rounded-xl px-4 py-2.5">
          {data.strategy_description}
        </p>
      )}

      {isLoading ? (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {Array.from({ length: 10 }).map((_, i) => (
              <Skeleton key={i} className="h-16 rounded-xl" />
            ))}
          </div>
          <Skeleton className="h-60 rounded-2xl" />
        </>
      ) : isError || !data ? (
        <div className="bg-card border border-border rounded-2xl p-8 text-center text-muted-foreground text-sm flex flex-col items-center gap-2">
          <AlertCircle size={18} className="opacity-40" />
          <span>Backtest data unavailable</span>
        </div>
      ) : data.error ? (
        <div className="bg-card border border-border rounded-2xl p-8 text-center text-muted-foreground text-sm flex flex-col items-center gap-2">
          <AlertCircle size={18} className="opacity-40" />
          <span>{data.error}</span>
        </div>
      ) : (
        <>
          {/* Stats cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {statCards.map(({ label, value, sub, color }) => (
              <div key={label} className="bg-card border border-border rounded-xl px-3 py-3">
                <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">
                  {label}
                </div>
                <div className={`text-sm font-semibold font-mono ${color}`}>{value}</div>
                <div className="text-[10px] text-muted-foreground mt-0.5">{sub}</div>
              </div>
            ))}
          </div>

          {/* Equity curve vs benchmark with trade markers */}
          {data.equity_curve.length > 1 ? (
            <div className="bg-card border border-border rounded-2xl p-4">
              <ResponsiveContainer width="100%" height={240}>
                <ComposedChart
                  data={data.equity_curve}
                  margin={{ top: 8, right: 16, bottom: 0, left: 8 }}
                >
                  <defs>
                    <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--color-buy)" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="var(--color-buy)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border/40" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 10 }}
                    className="text-muted-foreground"
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    domain={["auto", "auto"]}
                    tickFormatter={(v: number) => `${(v - 100).toFixed(0)}%`}
                    tick={{ fontSize: 10 }}
                    className="text-muted-foreground"
                  />
                  <Tooltip content={<EquityTooltip />} />
                  <ReferenceLine y={100} stroke="var(--color-border)" strokeWidth={1.5} />
                  <Line
                    type="monotone"
                    dataKey="benchmark"
                    stroke="var(--color-muted-foreground)"
                    strokeWidth={1.5}
                    strokeDasharray="4 3"
                    dot={false}
                    activeDot={false}
                  />
                  <Area
                    type="monotone"
                    dataKey="equity"
                    stroke="var(--color-buy)"
                    strokeWidth={2}
                    fill="url(#equityGrad)"
                    dot={false}
                    activeDot={{ r: 3 }}
                  />
                  {data.trades.map((t, i) =>
                    eqByDate.has(t.date_entry) ? (
                      <ReferenceDot
                        key={`entry-${i}`}
                        x={t.date_entry}
                        y={eqByDate.get(t.date_entry)!}
                        r={4}
                        fill="var(--color-buy)"
                        stroke="var(--color-card)"
                        strokeWidth={1.5}
                      />
                    ) : null
                  )}
                  {data.trades.map((t, i) =>
                    eqByDate.has(t.date_exit) ? (
                      <ReferenceDot
                        key={`exit-${i}`}
                        x={t.date_exit}
                        y={eqByDate.get(t.date_exit)!}
                        r={4}
                        fill="var(--color-sell)"
                        stroke="var(--color-card)"
                        strokeWidth={1.5}
                      />
                    ) : null
                  )}
                </ComposedChart>
              </ResponsiveContainer>
              <p className="text-[10px] text-muted-foreground text-center mt-2">
                Green area = strategy equity (starts at ₹100) · dashed grey = buy &amp; hold ·
                dots = trade entries/exits · {data.stats.num_trades} trades · {PERIOD_LABELS[period]} window
              </p>
            </div>
          ) : (
            <div className="bg-card border border-border rounded-2xl p-8 text-center text-muted-foreground text-sm">
              No trades generated in this period
            </div>
          )}

          {/* Trade log */}
          {data.trades.length > 0 && (
            <div className="bg-muted/30 rounded-xl border border-border overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border/50 text-muted-foreground">
                    <th className="text-left px-3 py-2 font-medium">Entry</th>
                    <th className="text-left px-3 py-2 font-medium">Exit</th>
                    <th className="text-right px-3 py-2 font-medium">Entry ₹</th>
                    <th className="text-right px-3 py-2 font-medium">Exit ₹</th>
                    <th className="text-right px-3 py-2 font-medium">P&amp;L %</th>
                  </tr>
                </thead>
                <tbody>
                  {data.trades.map((t, i) => (
                    <tr key={i} className="border-b border-border/30 last:border-0">
                      <td className="px-3 py-1.5 font-mono">{t.date_entry}</td>
                      <td className="px-3 py-1.5 font-mono">{t.date_exit}</td>
                      <td className="px-3 py-1.5 text-right font-mono">
                        ₹{t.entry_price.toLocaleString("en-IN")}
                      </td>
                      <td className="px-3 py-1.5 text-right font-mono">
                        ₹{t.exit_price.toLocaleString("en-IN")}
                      </td>
                      <td
                        className={`px-3 py-1.5 text-right font-mono font-semibold ${
                          t.pnl_pct >= 0 ? "text-buy" : "text-sell"
                        }`}
                      >
                        {t.pnl_pct >= 0 ? "+" : ""}
                        {t.pnl_pct.toFixed(2)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <MethodologyNote title="How this backtest works">
            <p>
              Walk-forward simulation: each day the strategy sees only data up to that day
              (no look-ahead). Long-only, one position at a time, filled at the daily close.
            </p>
            <p>
              Not modelled: transaction costs, slippage, dividends, taxes. Past performance
              does not predict future results.
            </p>
          </MethodologyNote>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify types still flag only the page**

```bash
npx tsc --noEmit
```

Expected: errors only at the `BacktestPanel` call-site in `page.tsx` (missing `strategy`/`onStrategyChange` props) — fixed in Task 11.

- [ ] **Step 3: Commit**

```bash
git add src/components/analysis/BacktestPanel.tsx
git commit -m "feat(frontend): backtest strategy toggle, benchmark, markers, 10-stat grid"
```

---

### Task 10: Confluence tab — SystemsStrip + legend

**Files:**
- Create: `frontend/src/components/analysis/SystemsStrip.tsx`
- Modify: `frontend/src/components/analysis/ConfluenceGrid.tsx:147-149`
- Test: `frontend/src/test/SystemsStrip.test.tsx`

- [ ] **Step 1: Write failing test**

Create `frontend/src/test/SystemsStrip.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SystemsStrip } from "@/components/analysis/SystemsStrip";

describe("SystemsStrip", () => {
  it("renders all three system verdicts", () => {
    render(
      <SystemsStrip
        technical={{ signal: "BUY", confidence: 72 }}
        fundamental={{ grade: "Strong", score: 70 }}
        ml={{ direction: "UP", probability: 0.62 }}
        onSelectTab={() => {}}
      />
    );
    expect(screen.getByText("BUY · 72%")).toBeInTheDocument();
    expect(screen.getByText("Strong · 70")).toBeInTheDocument();
    expect(screen.getByText("UP · 62%")).toBeInTheDocument();
  });

  it("navigates to the tab on click", () => {
    const onSelect = vi.fn();
    render(
      <SystemsStrip
        technical={{ signal: "BUY", confidence: 72 }}
        fundamental={null}
        ml={null}
        onSelectTab={onSelect}
      />
    );
    fireEvent.click(screen.getByText("Technical"));
    expect(onSelect).toHaveBeenCalledWith("technical");
  });

  it("shows placeholders for missing systems", () => {
    render(<SystemsStrip technical={null} fundamental={null} ml={null} onSelectTab={() => {}} />);
    expect(screen.getAllByText("—")).toHaveLength(3);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
npx vitest run src/test/SystemsStrip.test.tsx
```

Expected: FAIL — module not found.

- [ ] **Step 3: Create `SystemsStrip.tsx`**

```tsx
import { cn } from "@/lib/utils";
import { Activity, Building2, Cpu } from "lucide-react";

interface Props {
  technical: { signal: string; confidence: number } | null;
  fundamental: { grade: string; score?: number } | null;
  ml: { direction: string | null; probability: number | null } | null;
  onSelectTab: (tab: string) => void;
}

function toneClass(value: string | null | undefined): string {
  if (!value) return "text-muted-foreground";
  if (["BUY", "UP", "Strong"].includes(value)) return "text-buy";
  if (["SELL", "DOWN", "Weak"].includes(value)) return "text-sell";
  return "text-hold";
}

export function SystemsStrip({ technical, fundamental, ml, onSelectTab }: Props) {
  const systems = [
    {
      tab: "technical",
      label: "Technical",
      icon: Activity,
      key: technical?.signal ?? null,
      value: technical ? `${technical.signal} · ${technical.confidence}%` : "—",
    },
    {
      tab: "fundamental",
      label: "Fundamental",
      icon: Building2,
      key: fundamental?.grade ?? null,
      value: fundamental
        ? `${fundamental.grade}${fundamental.score != null ? ` · ${Math.round(fundamental.score)}` : ""}`
        : "—",
    },
    {
      tab: "ml",
      label: "ML Model",
      icon: Cpu,
      key: ml?.direction ?? null,
      value: ml?.direction
        ? `${ml.direction}${ml.probability != null ? ` · ${Math.round(ml.probability * 100)}%` : ""}`
        : "—",
    },
  ];

  return (
    <div className="grid grid-cols-3 gap-3">
      {systems.map(({ tab, label, icon: Icon, key, value }) => (
        <button
          key={tab}
          onClick={() => onSelectTab(tab)}
          className="bg-card border border-border rounded-xl px-3 py-2.5 text-left hover:border-foreground/20 transition-colors"
        >
          <span className="flex items-center gap-1.5 text-[10px] text-muted-foreground uppercase tracking-wider">
            <Icon size={11} />
            {label}
          </span>
          <span className={cn("block text-sm font-semibold mt-0.5", toneClass(key))}>{value}</span>
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
npx vitest run src/test/SystemsStrip.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Replace the hover-only tip in `ConfluenceGrid.tsx`**

Replace (lines 147–149):

```tsx
      <p className="text-xs text-muted-foreground">
        Green = bullish points, Red = bearish. Hover cells for indicator detail. Cached 10 min.
      </p>
```

with:

```tsx
      <div className="flex items-center gap-4 text-xs text-muted-foreground flex-wrap">
        <span className="inline-flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-buy/15 border border-buy/20 inline-block" /> Bullish points
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-sell/15 border border-sell/20 inline-block" /> Bearish points
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-muted/60 border border-border inline-block" /> Neutral
        </span>
        <span className="ml-auto">1W/1M candles resampled from daily · cached 10 min</span>
      </div>
```

- [ ] **Step 6: Verify and commit**

```bash
npx vitest run && git add src/components/analysis/SystemsStrip.tsx src/components/analysis/ConfluenceGrid.tsx src/test/SystemsStrip.test.tsx
git commit -m "feat(frontend): cross-system strip + tap-friendly confluence legend"
```

---

### Task 11: Page wiring — controlled tabs, strategy state, methodology notes

**Files:**
- Modify: `frontend/src/app/dashboard/stocks/[ticker]/page.tsx`

- [ ] **Step 1: Add state, handoff, and new imports**

In `frontend/src/app/dashboard/stocks/[ticker]/page.tsx`:

Add imports:

```tsx
import { MethodologyNote } from "@/components/analysis/MethodologyNote";
import { SystemsStrip } from "@/components/analysis/SystemsStrip";
import type { BacktestStrategy } from "@/lib/api/analysis";
```

After the `const [activeTab, setActiveTab] = useState("technical");` line, add:

```tsx
  const [backtestStrategy, setBacktestStrategy] = useState<BacktestStrategy>("indicator");
  const backtestMLModel = useCallback(() => {
    setBacktestStrategy("ml");
    setActiveTab("backtest");
  }, []);
```

Make the tabs controlled — replace:

```tsx
      <Tabs defaultValue="technical" className="flex-col" onValueChange={setActiveTab}>
```

with:

```tsx
      <Tabs value={activeTab} className="flex-col" onValueChange={setActiveTab}>
```

- [ ] **Step 2: Wire the ML card and BacktestPanel**

Replace `<MLPredictionCard data={ml} />` with:

```tsx
              <MLPredictionCard data={ml} onBacktestModel={backtestMLModel} />
```

Replace `<BacktestPanel ticker={ticker} enabled={activeTab === "backtest"} />` with:

```tsx
          <BacktestPanel
            ticker={ticker}
            enabled={activeTab === "backtest"}
            strategy={backtestStrategy}
            onStrategyChange={setBacktestStrategy}
          />
```

- [ ] **Step 3: Add SystemsStrip to the Confluence tab**

Replace the Confluence `TabsContent` body:

```tsx
        <TabsContent value="confluence" className="mt-4 space-y-4">
          <SystemsStrip
            technical={signal ? { signal: signal.signal, confidence: signal.confidence } : null}
            fundamental={fundamentals?.grade ? { grade: fundamentals.grade, score: fundamentals.score } : null}
            ml={ml ? { direction: ml.direction, probability: ml.probability } : null}
            onSelectTab={setActiveTab}
          />
          {confluenceLoading ? (
            <ConfluenceGridSkeleton />
          ) : confluence ? (
            <ConfluenceGrid data={confluence} />
          ) : confluenceError ? (
            <ConfluenceGridError />
          ) : null}
          <MethodologyNote>
            <p>
              The same six-indicator signal engine runs on three timeframes: 1D (last ~3 months
              of daily candles), 1W (weekly candles over 2 years), and 1M (monthly candles over
              5 years), all resampled from one daily fetch. Agreement across timeframes is
              summarised as the confluence strength above.
            </p>
          </MethodologyNote>
        </TabsContent>
```

- [ ] **Step 4: Add MethodologyNotes to the Technical, Fundamental, and ML tabs**

Technical tab — after the closing `</div>` of the two-column grid (inside the `signal ?` branch), add:

```tsx
              <MethodologyNote>
                <p>
                  Six indicators each contribute signed points (RSI, MACD crossover, EMA trend
                  9/21/50/200, Bollinger Bands, support/resistance, OBV). The sum is normalised
                  to a 0–100 score: above 60 = BUY, below 40 = SELL, otherwise HOLD.
                </p>
                <p>Stop-loss and target are derived from ATR(14): 1.5× ATR stop, 3× ATR target on BUY signals.</p>
              </MethodologyNote>
```

Fundamental tab — after `<FundamentalsPanel ... />` (inside the `fundamentals ?` branch), add:

```tsx
              <MethodologyNote>
                <p>
                  Data from screener.in and Yahoo Finance, cached ~4 hours. The 0–100 score
                  awards points for P/E, ROE, debt/equity, revenue growth, net margin (15 each)
                  and analyst view (25). Card colours reflect each metric&apos;s contribution.
                </p>
              </MethodologyNote>
```

ML tab — after `<MLPredictionCard ... />`, add:

```tsx
              <MethodologyNote>
                <p>
                  A RandomForest classifier is trained per request on 12 technical features over
                  the full history, with a time-ordered 80/20 split (no shuffling, no leakage).
                  It predicts whether tomorrow&apos;s close will be higher than today&apos;s.
                  Accuracy is measured on the held-out 20%. Cached 1 hour.
                </p>
              </MethodologyNote>
```

- [ ] **Step 5: Full frontend verification**

```bash
cd "/Users/divyanshuagarwal/Downloads/frist workflow/frontend"
npx tsc --noEmit && npm run lint && npx vitest run && npm run build
```

Expected: all clean. This is the first commit where tsc must be fully green.

- [ ] **Step 6: Commit**

```bash
git add src/app/dashboard/stocks
git commit -m "feat(frontend): wire strategy state, ML→backtest handoff, methodology notes"
```

---

### Task 12: README, final verification, PR

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README**

In `README.md`, find the section describing analysis features / the backtest (search for "backtest"; if absent, add under the existing features/architecture section):

```markdown
### Backtesting

`/api/v1/analysis/backtest?ticker=…&period=6mo|1y|2y&strategy=indicator|ml` runs a
walk-forward, long-only backtest on daily OHLCV (close-price fills, no look-ahead):

- **indicator** (default) — trades the composite technical signal (RSI, MACD, EMA trend,
  Bollinger, S/R, OBV); BUY > 60 to enter, SELL < 40 to exit.
- **ml** — trades a RandomForest next-day direction model retrained every 21 bars
  walk-forward; enters at P(up) ≥ 55%, exits at P(up) ≤ 45%. Needs ≥ ~141 daily bars.

The response includes a buy-&-hold benchmark series and stats: total return, win rate,
avg gain/loss, max drawdown, Sharpe, profit factor, exposure %, avg holding days.
```

- [ ] **Step 2: Full-stack verification**

```bash
cd "/Users/divyanshuagarwal/Downloads/frist workflow"
python -m pytest tests/ -q
ruff check backend tools
cd frontend && npx tsc --noEmit && npm run lint && npx vitest run && npm run build
```

Expected: everything green.

- [ ] **Step 3: Commit, push, open PR**

```bash
cd "/Users/divyanshuagarwal/Downloads/frist workflow"
git add README.md
git commit -m "docs: document backtest strategies and expanded stats"
git push -u origin feature/analysis-tabs-redesign
gh pr create --title "Analysis tabs redesign: ML/indicator backtest, benchmark, explainability" --body "$(cat <<'EOF'
## Summary
- Backtest engine: strategy param (indicator | ml), walk-forward RandomForest strategy with monthly retraining, buy-&-hold benchmark, Sharpe/profit factor/exposure/avg-hold stats
- Backtest tab: strategy toggle, benchmark overlay, trade entry/exit markers, 10-stat grid, strategy description
- Technical tab: 0–100 score gauge, price-level rail, diverging indicator contribution bars
- Fundamental tab: scoring breakdown merged into tone-coded metric cards
- ML tab: confidence gauge with 50% anchor, all 12 features, honest accuracy context, "Backtest this model" handoff
- Confluence tab: cross-system strip, tap-friendly legend
- All tabs: collapsible "How this is computed" methodology notes

Spec: docs/superpowers/specs/2026-06-12-analysis-tabs-redesign-design.md

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

After merge: delete the branch (`git branch -d feature/analysis-tabs-redesign` and on GitHub) per the repo's single-branch workflow.
