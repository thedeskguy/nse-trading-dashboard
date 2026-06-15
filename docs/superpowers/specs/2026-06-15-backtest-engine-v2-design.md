# Backtest Engine v2 (Phase A) — Design Spec

**Date:** 2026-06-15
**Status:** Approved (design); pending implementation plan
**Owner:** Divyanshu

## 1. Summary

The current walk-forward backtester (`tools/backtester.py`) is long-only, enters
on BUY and **only** exits on SELL, fills at close with **no stops, no targets, no
position sizing**, and **force-closes** any open position at the last bar (hiding
it as a fake closed trade). This makes results unrealistic and gives users no view
of what's currently open.

Phase A upgrades the engine in place — same single-pass simulator and result
contract, extended — to add **risk-managed exits (ATR stop-loss / take-profit at a
minimum 1:3 risk:reward), a trailing stop, a trend/regime filter on entries,
fixed-fractional position sizing, richer metrics, and a real open-position
readout**. It applies to both existing strategies (`indicator`, `ml`).

New strategy presets (trend-following, mean-reversion, breakout) are **Phase B**, a
separate spec built on this engine.

## 2. Goals / Non-goals

**Goals**
- Realistic exits: ATR stop-loss + take-profit (≥ 1:3 R:R) + trailing stop, in
  addition to the existing SELL-signal exit.
- Trend/regime filter so BUYs are only taken with the trend (no counter-trend entries).
- Fixed-fractional position sizing (risk a fixed % of equity to the stop).
- Richer metrics: CAGR, Sortino, Calmar, best/worst trade, max consecutive losses.
- Surface the **currently-open position** distinctly (no force-close).
- Apply uniformly to `indicator` and `ml` strategies (shared sim loop).

**Non-goals (Phase A)**
- No transaction costs / slippage (explicitly deferred by the user).
- No new strategy presets (that's Phase B).
- No intraday fills — still daily close-price fills (a stop/target counts as hit
  when the daily close crosses it).
- No multi-position / pyramiding — still one long position at a time.

## 3. Tunable Parameters (defaults)

Centralized as named constants in `tools/backtester.py`:

```
TREND_EMA      = 200    # only enter long when close > EMA(200)
ATR_PERIOD     = 14
SL_ATR_MULT    = 2.0    # initial stop = entry − 2.0·ATR
RR_RATIO       = 3.0    # target = entry + RR_RATIO·(entry − stop)  → 1:3 minimum
TRAIL_ATR_MULT = 2.5    # trailing stop = highest-close-since-entry − 2.5·ATR
RISK_PCT       = 0.01   # risk 1% of equity to the stop per trade
```

`RR_RATIO = 3.0` encodes the required **1:3 minimum** reward:risk: with the stop
2·ATR below entry, the target sits 6·ATR above entry.

## 4. Engine Mechanics

The simulator stays a single forward pass over bars `warmup … end`. Per bar the
strategy still emits BUY/HOLD/SELL (`_indicator_signals` / `_ml_signals`
unchanged). The trade state machine changes:

### 4.1 Entry (BUY, flat)
- **Trend filter:** enter only if `close > EMA(TREND_EMA)` at the entry bar.
  Otherwise skip the BUY (stay flat).
- **Stop / target:** `atr = ATR(14)` at entry bar.
  `stop = entry − SL_ATR_MULT·atr`; `risk = entry − stop`;
  `target = entry + RR_RATIO·risk`.
- **Sizing (fixed-fractional):** `stop_dist_pct = risk / entry`;
  `alloc = min(1.0, RISK_PCT / stop_dist_pct)`. Invest `alloc·equity`; the rest is
  cash (earns nothing). Record `entry_high = entry` (high-water for trailing).

### 4.2 While long — exit checks each bar (priority order, first hit wins)
1. **Stop-loss / trailing:** `trail = entry_high − TRAIL_ATR_MULT·atr`;
   `effective_stop = max(stop, trail)`. If `close ≤ effective_stop` → exit at
   `close`, `exit_reason = "stop"` (or `"trail"` if the trailing level is the binding one).
2. **Take-profit:** if `close ≥ target` → exit at `close`, `exit_reason = "target"`.
3. **SELL signal:** if `signal == "SELL"` → exit at `close`, `exit_reason = "signal"`.
   Update `entry_high = max(entry_high, close)` each bar before the checks.

### 4.3 Equity (marked-to-market daily)
`equity = cash + invested·(close/entry)` while long; `equity = cash` when flat.
On exit, realize: `cash = equity`, `invested = 0`. Curve still starts at 100 with a
buy-&-hold benchmark normalised to 100 at the first signal bar (unchanged).

### 4.4 Open position (no force-close)
If still long at the final bar, **do not** synthesize a closing trade. Instead
return an `open_position` object and let the final equity point reflect the open
mark-to-market. `trades` contains only realised (closed) trades.

## 5. Result Contract (extends today's shape)

```jsonc
{
  "trades": [ { ...existing..., "exit_reason": "stop|target|trail|signal", "r_multiple": -1.0 } ],
  "open_position": {                       // null when flat at the end
    "date_entry": "2026-06-12",
    "entry_price": 772.45,
    "current_price": 777.0,
    "unrealized_pnl_pct": 0.59,
    "days_held": 3,
    "stop": 740.1,
    "target": 869.4,
    "exit_reason": null
  },
  "equity_curve": [ ...unchanged... ],
  "stats": {
    ...existing (num_trades, win_rate, total_return_pct, avg_gain/loss, max_drawdown_pct,
       sharpe_ratio, profit_factor, exposure_pct, avg_hold_days, buy_hold_return_pct)...,
    "cagr_pct": 0.0,
    "sortino_ratio": 0.0,
    "calmar_ratio": 0.0,
    "best_trade_pct": 0.0,
    "worst_trade_pct": 0.0,
    "max_consecutive_losses": 0
  },
  "strategy": "indicator",
  "strategy_description": "…updated to mention stops/target/trailing/trend filter/sizing…",
  "error": null
}
```

`r_multiple` = trade P&L ÷ initial risk (in price terms) — a natural fit now that
every trade has a defined stop. New metric formulas:
- **CAGR:** `(final_equity/100)^(252/n_bars) − 1`, as %.
- **Sortino:** mean daily return ÷ downside deviation × √252.
- **Calmar:** `cagr_pct / abs(max_drawdown_pct)` (null if drawdown is 0).
- **best/worst_trade_pct:** max/min closed-trade `pnl_pct`.
- **max_consecutive_losses:** longest run of `pnl_pct ≤ 0` closed trades.

## 6. Backend

`backend/routers/analysis.py` `/analysis/backtest` is unchanged in signature — it
already calls `run_backtest(df, strategy=…)` and returns the result. The extended
fields (`open_position`, new stats, `exit_reason`) flow through `clean_dict`
automatically. Cache key unchanged.

## 7. Frontend (`frontend/src/components/analysis/BacktestPanel.tsx`)

- **Open Position card** (only when `open_position` is non-null), shown above the
  equity chart: ticker, entry date/price, current price, **unrealized P&L %**
  (green/red), days held, stop & target with distance-to-each. Make it visually
  distinct from the closed-trades table so users see "you'd still be holding this."
- **Stats row:** add CAGR, Sortino, Calmar (mirror the existing stat-card style).
- **Trades table:** add an **Exit** column showing `exit_reason` (Stop / Target /
  Trail / Signal) with a subtle color (stop/trail = red-ish, target = green, signal = neutral).
- Update the "How this backtest works" methodology note to describe stops/target
  (1:3), trailing stop, trend filter, and sizing.
- Types updated in `frontend/src/lib/api/analysis.ts` (`BacktestStats` extended,
  new `OpenPosition` interface, `BacktestTrade` gains `exit_reason`/`r_multiple`,
  `BacktestResponse` gains `open_position`).

## 8. Testing (pytest, `tests/`)

Unit tests on `run_backtest` with small hand-built OHLCV frames (deterministic):
- **Stop-loss exit:** a drop below `entry − 2·ATR` closes the trade with `exit_reason="stop"`.
- **Take-profit exit:** a rise to the 1:3 target closes with `exit_reason="target"` and `r_multiple ≈ 3`.
- **Trailing stop:** price runs up then pulls back past the trail → `exit_reason="trail"`, locks a gain.
- **SELL-signal exit:** still works (`exit_reason="signal"`).
- **Trend filter:** a BUY while `close < EMA200` does **not** open a trade.
- **Position sizing:** wider stop → smaller `alloc`; verify the equity move on a
  win is `alloc · price-move`, and a stop-out loses ≈ `RISK_PCT` of equity.
- **Open position:** a frame ending mid-trade returns a populated `open_position`
  and no synthetic closing trade.
- **Metrics:** CAGR/Sortino/Calmar/best/worst/max-consec-losses on a known series.
- Existing tests still pass; `ml` strategy still runs (now with the v2 exits).

Signal generation (`generate_signals`, `compute_indicators`) is reused as-is; ATR
and EMA-200 come from `compute_indicators` (verify they're present, else compute
ATR(14)/EMA(200) in the backtester).

## 9. Phasing
- **Phase A (this spec):** engine v2 + open position, on the existing `indicator`/`ml` strategies.
- **Phase B (separate):** new selectable strategy presets — trend-following (MA
  crossover), mean-reversion (RSI bounce), breakout (Donchian/52-week) — on this engine.

## 10. Out of Scope (later)
- Transaction costs / slippage.
- Intraday/stop-gap fills, multiple concurrent positions, pyramiding.
- Walk-forward parameter optimization of the ATR/RR/risk constants.
