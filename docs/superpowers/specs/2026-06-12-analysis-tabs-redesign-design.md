# Analysis Tabs Redesign — Design Spec

**Date:** 2026-06-12
**Scope:** Stock detail page (`/dashboard/stocks/[ticker]`) — Technical, Fundamental, ML Prediction, Confluence, and Backtest tabs; plus the backtest engine (`tools/backtester.py`) and `/analysis/backtest` endpoint.

## Goals

1. **Visual/UX upgrade** — richer, more legible rendering across all five tabs.
2. **Backtest substance** — buy-&-hold benchmark, trade markers, expanded stats.
3. **ML-strategy backtest** — let the backtest trade the RandomForest model so it can be compared against the indicator strategy.
4. **Explainability** — every tab discloses its own methodology so nobody has to ask "what is this number / what does the backtest trade?"

## Background (current behaviour)

- The backtest trades the **rule-based indicator signal** (`tools/generate_signals.py`: composite 0–100 score from RSI, MACD, EMA trend, Bollinger, S/R, OBV), walk-forward after a 50-bar warmup, long-only, BUY-to-enter / SELL-to-exit, mark-to-market daily from ₹100. The ML model is never traded.
- The ML tab (`MLPredictionCard`) trains a per-request RandomForest (`tools/ml_predictor.py`) on full history with a time-ordered 80/20 split; accuracy shown is test-set accuracy.
- Confluence is **multi-timeframe** (1D/1W/1M of the same indicator engine), not cross-system.
- `VerdictBanner` already exists as a shared verdict-header pattern.

---

## Backend changes

### 1. `tools/backtester.py` — strategy parameter + benchmark + stats

`run_backtest(df, strategy="indicator")` where `strategy ∈ {"indicator", "ml"}`.

**Structure:** split into three phases — (a) signal generation (varies by strategy), (b) trade simulation + daily MTM equity (shared, unchanged logic), (c) stats (shared, expanded).

**Indicator strategy** — unchanged: `generate_signal(df.iloc[:i+1])["signal"]` per bar from `WARMUP=50`.

**ML strategy** — walk-forward with **monthly retraining** (every 21 bars) to keep latency acceptable (~12 trainings for 1Y, ~24 for 2Y):

- Warmup: `ML_WARMUP = 120` bars (the predictor needs ≥ 60 clean training rows; 120 gives margin for indicator NaNs).
- At each retrain point `i` (i = ML_WARMUP, ML_WARMUP+21, …): build features once for the whole df via `build_features()`, train `RandomForestClassifier` (same hyperparameters as `ml_predictor.py`, `random_state=42`) on clean rows up to and including `i-1` (target uses `shift(-1)`, so row `i-1`'s target — whether `close[i] > close[i-1]` — is known by the close of bar `i`; no look-ahead).
- For bars `i … i+20`: predict `P(up)` from that bar's feature row (NaNs filled with training-set column means, same as `ml_predictor`).
- Signal mapping with hysteresis to avoid churn: `P(up) ≥ 0.55 → BUY`, `P(up) ≤ 0.45 → SELL`, else `HOLD`.
- If `df` has fewer than `ML_WARMUP + 21` rows, return the empty-result shape with `"error": "Not enough history for ML backtest — use 1y or 2y period."`.

**Benchmark (both strategies):** each `equity_curve` point gains a `benchmark` field — buy-&-hold of the underlying normalised to 100 at the first post-warmup bar: `100 * close[i] / close[warmup]`.

**New stats** (added to existing six):

| Field | Definition |
|---|---|
| `sharpe_ratio` | mean(daily equity returns) / std × √252; 0.0 if std = 0 or < 2 points |
| `profit_factor` | gross gains / abs(gross losses); `null` when no losing trades |
| `exposure_pct` | % of post-warmup bars spent long |
| `avg_hold_days` | mean calendar days between entry and exit across trades |
| `buy_hold_return_pct` | benchmark total return over the same window |

**Response additions:** `strategy` (echo) and `strategy_description` (one-line human text, e.g. "Trades the composite technical indicator signal (RSI, MACD, EMA, Bollinger, S/R, OBV). Long-only, BUY to enter, SELL to exit." / "Trades a RandomForest next-day direction model, retrained monthly on a walk-forward basis. Enters at P(up) ≥ 55%, exits at P(up) ≤ 45%.").

### 2. `backend/routers/analysis.py` — `/analysis/backtest`

- New query param: `strategy: str = Query("indicator", pattern=r"^(indicator|ml)$")`.
- Cache key: `backtest:{ticker}:{period}:{strategy}`. TTL unchanged (`adaptive_ttl(21600)`).
- Add `@limiter.limit("10/minute")` to the endpoint (ML mode is compute-heavier; the endpoint currently has no rate limit).
- Docstring updated to describe both strategies.

---

## Frontend changes

### Shared: `MethodologyNote` component (new)

`frontend/src/components/analysis/MethodologyNote.tsx` — a collapsible "How this is computed" footnote (native `<details>`, muted styling, consistent across tabs). Each tab passes its own 2–4 sentence explanation including data source and cache window. This is the consistency/explainability backbone; `VerdictBanner` remains the shared header.

### Technical tab

- **Score gauge:** horizontal zone bar (SELL < 40 / HOLD 40–60 / BUY > 60 zones tinted sell/hold/buy) with a marker at the composite score, replacing the plain confidence bar in `SignalCard`.
- **Price-level rail:** stop-loss → entry → target rendered on one horizontal rail with the current price marked, replacing the three disconnected cards.
- **`IndicatorBreakdown`:** signed diverging contribution bars (points relative to each component's max, bearish left / bullish right of a centre line) instead of badge-only points, keeping value + label text.
- MethodologyNote: composite scoring, ATR-based stop/target, data window.

### Fundamental tab

- Merge presentation of `FundamentalsPanel` + `FundamentalsBreakdown`: each metric card gets a colour accent (buy/hold/sell tint) **derived from the existing `score_fundamentals` breakdown** where the metric maps to a scoring component; unmapped metrics stay neutral. The breakdown's threshold labels become the card sublabels — no invented sector averages (no reliable peer data source available).
- Grade + score stay in the `VerdictBanner`; the separate breakdown list collapses into the cards.
- MethodologyNote: sources (screener.in + yfinance), scoring thresholds, 4h cache.

### ML Prediction tab

- **Confidence gauge** with a 50% reference line (a coin-flip anchor) replacing the plain probability bar.
- **All 12 features** shown (not top 4), sorted by importance, with readable names (e.g. `ema200_dist` → "Distance from EMA 200").
- **Honest accuracy context:** "62% accuracy on the last N sessions (time-ordered hold-out)" using `train_samples`/`test_samples` already in the response, plus a caveat line ("next-day direction is near-random; treat < 55% as noise").
- **"Backtest this model →" button** — switches the page to the Backtest tab with the ML strategy preselected.

### Confluence tab

- Keep the existing heatmap and summary banner (already strong).
- Add a **cross-system strip** above the heatmap: Technical verdict · Fundamental grade · ML direction, from queries the page already runs (no new requests). Each links to its tab.
- Replace the hover-only hint with a tap-friendly legend (mobile users can't hover).
- MethodologyNote: 1W/1M resampled from one 5y daily fetch; what each timeframe means.

### Backtest tab (`BacktestPanel`)

- **Strategy toggle** (Indicator / ML) beside the period selector; drives the `strategy` query param. Preselectable from the ML tab via page-level state.
- **Strategy description line** rendered from `strategy_description` — directly answers "what is this trading?".
- **Benchmark line:** grey buy-&-hold line overlaid on the equity curve (`benchmark` key); tooltip shows both values; caption gains "vs Buy & Hold +X%".
- **Trade markers:** entry (▲ buy-colour) and exit (▼ sell-colour) dots on the curve via Recharts `ReferenceDot`s derived from the existing `trades` array.
- **Expanded stat grid:** 10 cards — existing 6 + Sharpe, Profit Factor, Exposure %, Avg Hold Days — each with a one-line subtext defining the metric. "Total Return" card shows the buy-&-hold delta as a sublabel.
- **ML error state:** when the API returns the not-enough-history error, show a friendly notice suggesting a longer period.
- MethodologyNote: walk-forward mechanics, no look-ahead, no transaction costs/slippage (disclosed), close-price fills.

### API client (`frontend/src/lib/api/analysis.ts`)

- `useBacktest(ticker, period, strategy, enabled)`; `strategy` joins the query key.
- Type updates: `BacktestResponse.stats` extra fields, `equity_curve[].benchmark`, `strategy`, `strategy_description`, optional `error`.

### Page (`[ticker]/page.tsx`)

- New state: `backtestStrategy`, passed to `BacktestPanel` and settable by `MLPredictionCard`'s button (also sets `activeTab = "backtest"`).

---

## Error handling

- ML backtest insufficient history → structured error in the 200 response (matches `ml_predictor`'s pattern), rendered as a notice, not a crash.
- All existing skeleton / error states preserved; new chart elements degrade gracefully when `trades` is empty (no markers, benchmark still drawn).
- Strategy param validation is regex-enforced at the router (422 on bad input).

## Testing

- **Backend (pytest):** ML-strategy backtest on a synthetic deterministic DataFrame (seeded) — asserts signal hysteresis, retrain cadence boundaries, and no look-ahead (training rows end at `i-2`); benchmark normalisation; new stat math (Sharpe, profit factor, exposure, avg hold) on hand-built trade fixtures; insufficient-history error shape; router strategy-param validation.
- **Frontend:** `npx tsc --noEmit`, eslint, `next build` (per repo CI gates). Manual verification of both strategy toggles and the ML→Backtest handoff.

## Out of scope

- Transaction costs / slippage modelling (disclosed in MethodologyNote instead).
- Short-selling or position sizing.
- Sector/peer comparative fundamentals (no data source).
- Scanner or Options pages.

## Rollout

Single feature branch `feature/analysis-tabs-redesign` → PR → merge → delete branch (per repo git workflow). Update `README.md` with the new backtest capabilities.
