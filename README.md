# NSE/BSE Trading Dashboard

A **buy-side only** decision-support tool for Indian market participants. Combines real-time OHLCV data from Angel One SmartAPI, technical analysis, fundamental data, ML price prediction, and options analysis — without placing any orders.

## Dashboards

| Dashboard | File | Purpose |
|---|---|---|
| Trading Dashboard | `dashboard.py` | Single-stock deep-dive: price chart, technical/fundamental/ML signals, fundamentals |
| Index Options | `pages/index_options.py` | Buy CALL or PUT on NIFTY / BANKNIFTY / MIDCPNIFTY with OI chart, premium view |

**What it does NOT do:** Short selling, futures, intraday scalping, or order placement.

---

## Features

### Equity & Options
- **Real-time OHLCV** — Angel One SmartAPI as primary source (no delay); auto-falls back to Yahoo Finance (~15 min delay) if credentials are missing or the API fails
- **Token lookup cache** — `searchScrip`-based token resolution cached to `.tmp/angel_tokens.json`; no large instrument-master download needed
- **Live options chain** — OI, LTP, bid/ask for NIFTY, BANKNIFTY, and MIDCPNIFTY via Angel One SmartAPI
- **Put-Call Ratio (PCR)** and **Max Pain** computation per expiry
- **OI chart** — visual call/put open interest across strikes
- **Multi-indicator signal engine** — RSI, MACD, EMA (9/21/50/200), Bollinger Bands, Support/Resistance, OBV
- **Confidence score (0–100%)** — composite score mapped to BUY / HOLD / SELL
- **ATR-based entry/SL/target** — stops calibrated to each stock's actual volatility
- **Unified stock search** — search all 2200+ NSE-listed equities by company name or ticker in a single dropdown (sourced from NSE equity list)
- **Three independent signals** — Technical, Fundamental, and ML cards shown side-by-side with individual BUY/SELL/HOLD
- **Fundamental analysis** — PE, ROE, D/E, revenue growth, profit margin, analyst targets scored 0–100; only shows available data
- **ML price direction predictor** — Random Forest trained on 12 technical features; predicts next-day up/down
- **OI tornado chart** — back-to-back CALL/PUT open interest across strikes with ATM reference line

### News Sentiment

A dedicated **Market Sentiment** page (`/dashboard/sentiment`) surfaces news-driven bias for a stock and its macro context — without blending them into a single number:

- **Independent readouts, never blended** — a stock's own news sentiment (its upside/downside call), **its industry/sector** ("how's the industry doing"), plus India and world market context, each shown side by side. The stock view pairs the stock gauge with its sector gauge; India and world sit below as macro context. The sector is resolved per ticker (yfinance) and omitted gracefully when unknown.
- **Each readout:** a score (−100…+100), a label (Bullish / Neutral / Bearish), a confidence (0–100, based on article count and signal agreement), and the top headlines that drove it. Fewer than 3 usable articles → "Insufficient recent news" state; no fabricated signal is shown.
- **100% free, no paid APIs required.** Market scopes use free RSS feeds — Moneycontrol, Economic Times, Business Standard, LiveMint (India); MarketWatch, CNBC, Reuters (world). **Per-stock** sentiment uses a free **Google News RSS search** by company name (e.g. `Rajesh Exports stock`, India-localized), restricted to the **last 30 days** so the readout reflects the latest news rather than evergreen "share price" pages, supplemented by the market RSS pool. Optional free-tier GNews enrichment activates when a `NEWS_API_KEY` env var is set; absent → RSS/Google-News only, no degraded behaviour.
- **Scoring engine:** with a free `HF_TOKEN` set, per-headline scoring uses **FinBERT** (`ProsusAI/finbert`) via the Hugging Face Inference API — finance-trained, so "lower circuit" / "misses estimates" read correctly; without it (or on rate-limit/error) it falls back to **VADER**. Each readout reports `scored_by` (`finbert` | `vader`).
- **Nightly precompute:** a free GitHub Actions job (`sentiment-pipeline.yml`, 17:00 IST) scores India/world + the Nifty 50 + their sectors with **local FinBERT** into Supabase `sentiment_snapshots`; the backend reads this store first (instant, FinBERT-quality for common names) and falls back to on-demand HF/VADER for the long tail.
- **Backend endpoints:** `GET /api/v1/sentiment/market?scope=india|world` and `GET /api/v1/sentiment/stock?ticker=…`
- News-sentiment bias only — not investment advice.

### Trading Chart

TradingView-style chart (lightweight-charts) on each stock page:

- 14 indicators — SMA, EMA, WMA, HMA, Supertrend, Bollinger, VWAP (overlays);
  RSI, MACD, Stochastic, ADX, ATR, OBV (panels, max 2)
- Full per-indicator settings: periods, price source (close/open/hl2/hlc3/ohlc4),
  per-line colors, line width, and editable overbought/oversold levels
- Volume histogram, TradingView-style legends with live values and
  hide/settings/remove controls, shaded OB/OS bands in oscillator panes
- Layout persists in localStorage across sessions and tickers

---

## Data Sources

| Data | Source | Latency |
|---|---|---|
| NIFTY / BANKNIFTY spot & options chain | Angel One SmartAPI | Real-time |
| Equity OHLCV (all intervals) | Angel One SmartAPI (primary) | Real-time |
| Equity OHLCV (fallback) | Yahoo Finance (`yfinance`) | ~15 min delay |
| Fundamental metrics (PE, ROE, etc.) | Yahoo Finance (`yfinance`) | Daily |
| Instrument token lookup | Angel One `searchScrip` | Cached to disk |

---

## Setup

### 1. Clone and create a virtual environment

```bash
git clone <your-repo-url>
cd <repo-folder>
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure credentials

```bash
cp .env.example .env
```

Open `.env` and fill in your Angel One SmartAPI credentials:

```
ANGEL_API_KEY=your_api_key
ANGEL_CLIENT_ID=your_client_id
ANGEL_MPIN=your_mpin
ANGEL_TOTP_SECRET=your_totp_secret
```

> Angel One credentials are only required for the Index Options and Equity Scanner dashboards. The Mutual Funds dashboard requires no API key.

### 3. Run the dashboard

```bash
streamlit run dashboard.py
```

The Index Options page is accessible via the top navigation inside the app.


---

## Project Structure

```
.
├── dashboard.py               # Main entry point — equities deep-dive dashboard
├── pages/
│   └── index_options.py       # Index Options page (NIFTY / BANKNIFTY / MIDCPNIFTY)
├── tools/
│   ├── angel_auth.py          # Angel One SmartAPI authentication
│   ├── fetch_angel_ohlcv.py   # Real-time OHLCV via Angel One (with yfinance fallback)
│   ├── fetch_options_chain.py # Options chain + OI fetcher (Angel One master)
│   ├── fetch_stock_data.py    # OHLCV orchestrator (Angel primary → yfinance fallback)
│   ├── fetch_fundamentals.py  # Fundamental metrics via yfinance (PE, ROE, D/E, etc.)
│   ├── compute_indicators.py  # RSI, MACD, EMA, BB, OBV, S/R
│   ├── generate_signals.py    # Scoring engine → BUY/HOLD/SELL
│   ├── analyze_options.py     # PCR, Max Pain, strike/expiry selection
│   ├── ml_predictor.py        # Random Forest next-day direction predictor
│   ├── theme.py               # Plotly/Streamlit dark theme helpers
│   ├── stock_lists.py         # Nifty 500 stock universe (used by EOD pipeline)
│   ├── price_store.py         # Supabase read/write helpers for price_history table
│   ├── eod_pipeline.py        # Nightly EOD OHLCV + scan precompute pipeline
│   ├── requirements-pipeline.txt  # Deps for eod_pipeline (CI/GitHub Actions)
│   ├── fetch_news.py          # Free RSS (+ optional GNews) news fetcher for sentiment
│   ├── sentiment_engine.py    # Per-headline scoring: FinBERT (HF API) or VADER
│   ├── aggregate_sentiment.py # Headlines → score/label/confidence readout
│   ├── finbert_local.py       # Local FinBERT scorer (nightly CI job only)
│   ├── sentiment_store.py     # Supabase read/write for sentiment_snapshots
│   ├── sentiment_pipeline.py  # Nightly FinBERT precompute (market + Nifty 50 + sectors)
│   └── requirements-sentiment.txt  # Deps for the nightly sentiment job (CI)
├── tests/
│   └── test_options_fixes.py  # Unit tests for options chain and signal edge cases
├── workflows/
│   └── trading_dashboard.md   # SOP for running the system
├── .streamlit/
│   └── config.toml            # Dark theme + headless config
├── requirements.txt
└── .env.example
```

---

## EOD Data Pipeline

Daily OHLCV for Nifty 500 + precomputed scanner signals are persisted in Supabase
(`price_history`, `scan_results`) by `.github/workflows/eod-pipeline.yml`
(16:15 IST, Mon–Fri). Backend endpoints read the store first and only hit
yfinance for a 5-day top-up during market hours, or as full fallback.

- First run / repair: Actions → "EOD price pipeline" → Run workflow → backfill: true
- Local run: `python tools/eod_pipeline.py --backfill` (needs SUPABASE_URL +
  SUPABASE_SERVICE_ROLE_KEY in `.env`)
- Required GitHub secrets: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`

### Keeping the Render free instance warm

Render's free plan sleeps after ~15 min idle (≈50 s cold start). Create a free
[UptimeRobot](https://uptimerobot.com) HTTP monitor on `GET /health` at a 10-minute
interval, or upgrade to Render Starter.

---

## Signal Engine (Equity)

Six indicators are scored and summed into a composite **Confidence** score:

| Indicator | Max Bullish | Max Bearish |
|---|---|---|
| RSI (14) | +15 | −15 |
| MACD (12/26/9) | +20 | −20 |
| EMA Trend (9/21/50/200) | +20 | −20 |
| Bollinger Bands (20, 2σ) | +15 | −15 |
| Support & Resistance | +15 | −15 |
| OBV | +15 | −15 |

```
Raw Score   = sum of all indicator scores  (range: −85 to +85)
Confidence  = ((Raw Score + 100) / 200) × 100
```

| Confidence | Signal |
|---|---|
| > 60% | BUY |
| 40–60% | HOLD |
| < 40% | SELL |

The equity scanner only surfaces **BUY** signals with R:R ≥ 1.5:1.

---

## Fundamental Scoring

Scored 0–100 across five dimensions:

| Dimension | Max Points |
|---|---|
| PE Ratio | 15 |
| ROE | 15 |
| Debt / Equity | 15 |
| Revenue Growth | 15 |
| Profit Margin | 15 |
| Analyst View (recommendation + price target upside) | 25 |

Grade: **Strong** (≥65) · **Fair** (45–64) · **Weak** (<45)

---

## ML Predictor

Trains a **Random Forest classifier** on 12 technical features derived from daily OHLCV:

`rsi, macd_hist, bb_pct, ema9_dist, ema21_dist, ema50_dist, ema200_dist, atr_pct, vol_change, ret_1d, ret_5d, obv_slope`

Target: next-day direction (up/down). No paid APIs — uses `scikit-learn` only.

---

## Backtesting

`/api/v1/analysis/backtest?ticker=…&period=6mo|1y|2y&strategy=indicator|ml` runs a
walk-forward, long-only backtest on daily OHLCV (close-price fills, no look-ahead).

### Strategies

- **indicator** (default) — trades the composite technical signal (RSI, MACD, EMA trend,
  Bollinger, S/R, OBV); BUY > 60 to enter, SELL < 40 to exit.
- **ml** — trades a RandomForest next-day direction model retrained every 21 bars
  walk-forward; enters at P(up) ≥ 55%, exits at P(up) ≤ 45%. Needs ≥ ~141 daily bars.

> **Planned (Phase B):** selectable strategy presets — trend-following, mean-reversion,
> and breakout — are not yet implemented.

### v2 Engine Behaviour

**Entry filter — uptrend gate:** a long position is only opened when the closing price
is above the 200-period EMA. Signals below EMA-200 are skipped entirely.

**Exit — first of four rules wins:**

| Rule | Trigger | Tag |
|---|---|---|
| Stop-loss | Price falls 2× ATR below entry | `stop` |
| Take-profit | Price rises 3× the initial risk (1:3 ATR target) | `target` |
| Trailing stop | Price retraces 2.5× ATR from the highest close since entry | `trail` |
| Signal exit | Strategy emits a SELL signal | `signal` |

Every closed trade record includes an `exit_reason` field set to one of the four tags above.

**Position sizing — fixed-fractional (1% risk per trade):** rather than going all-in,
each trade allocates only enough capital so that a 2×ATR adverse move equals 1% of
current equity. Allocation scales inversely with stop distance, so wider stops
automatically result in smaller position sizes.

**Open position reporting:** if a position is still open at the last bar it is **not**
force-closed. Instead it is returned as a separate `open_position` object containing
entry price, current price, unrealised P&L, days held, live stop level, and live
take-profit target.

### Metrics

The response includes a buy-&-hold benchmark series and the following stats:

| Metric | Description |
|---|---|
| Total return | Cumulative % gain over the period |
| CAGR | Annualised compound growth rate |
| Win rate | % of closed trades that were profitable |
| Avg gain / avg loss | Mean profit and mean loss per trade |
| Best / worst trade | Largest single winning and losing trade |
| Max drawdown | Peak-to-trough decline |
| Sharpe ratio | Risk-adjusted return (annualised, rf = 0) |
| Sortino ratio | Downside-deviation-adjusted return |
| Calmar ratio | CAGR ÷ max drawdown |
| Profit factor | Gross profits ÷ gross losses |
| Exposure % | Fraction of bars spent in a position |
| Avg holding days | Mean trade duration in calendar days |
| Max consecutive losses | Longest losing streak by trade count |

---

## Options Recommendation Logic

| Parameter | Intraday | Positional |
|---|---|---|
| Strike | ATM (confidence ≥ 70%) or 1-OTM | ATM (confidence ≥ 70%) or 1-OTM |
| Stop Loss | Premium × 65% (−35%) | Premium × 60% (−40%) |
| Target | Premium × 175% (+75%) | Premium × 200% (+100%) |

---

## Dependencies

```
streamlit >= 1.32.0
plotly >= 5.20.0
pandas >= 2.0.0
numpy >= 1.26.0
pandas-ta >= 0.3.14b0
yfinance >= 0.2.38
smartapi-python >= 1.3.4
pyotp >= 2.9.0
streamlit-autorefresh >= 1.0.1
scikit-learn >= 1.4.0
python-dotenv
requests
```

---

## Limitations

- **Not financial advice.** This is a decision-support tool only.
- **No order placement.** All execution must be done on your own broker platform.
- **Equity LTP** — real-time when Angel One credentials are present; ~15 min delayed via Yahoo Finance fallback.
- **IV not computed.** Angel One's API does not return IV directly; the column currently shows 0%.
- **No formal backtest.** Scoring weights and SL/target percentages are based on practitioner consensus, not a walk-forward simulation. Track accuracy in a paper-trading journal before risking capital.

---

## Roadmap

- [x] FinBERT sentiment scoring — on-demand (HF Inference API) + nightly local-FinBERT precompute into Supabase `sentiment_snapshots` (Phase 2 of News Sentiment). Trend-vs-yesterday deltas remain a future add.
- [ ] Compute Implied Volatility via Black-Scholes
- [ ] Backtest signal scoring over 3-year Nifty 100 history
- [ ] Options Greeks (Delta, Theta, Gamma) per recommendation
- [ ] Email / WhatsApp alerts on high-confidence BUY signals
- [ ] Intraday signal mode (15-min / 1-hour candles)
- [ ] Portfolio tracker for open positions
- [ ] Intraday signal mode with Angel One tick data

---

## Disclaimer

This software is provided for **educational and informational purposes only**. It does not constitute financial advice, investment recommendations, or a solicitation to buy or sell any security. Trading in derivatives involves substantial risk of loss. Always consult a registered financial advisor before making investment decisions.

---

*Built with Python · Streamlit · Angel One SmartAPI · Yahoo Finance · scikit-learn · pandas-ta · Plotly*
