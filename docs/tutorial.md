# NSE/BSE Trading Dashboard — Full Tutorial

> **Local only — not committed to Git.**
> This is your personal explanation guide for presenting or understanding this project end-to-end.

---

## What is this project?

A **buy-side only, decision-support trading dashboard** for Indian equity markets. It does NOT place orders. It helps you decide:

1. **Should I buy/hold/sell a stock?** (Equity Dashboard)
2. **Which CALL or PUT option should I buy on NIFTY/BANKNIFTY?** (Index Options Dashboard)

Built with: Python · Streamlit · Plotly · Angel One SmartAPI · Yahoo Finance · scikit-learn

---

## High-Level Architecture: WAT Framework

The project follows the **WAT (Workflows → Agents → Tools)** pattern:

```
workflows/          ← Markdown SOPs (the "what to do")
    trading_dashboard.md

[Agent = You / Claude]  ← Reads workflow, orchestrates tools, handles errors

tools/              ← Python scripts (the "how to do it")
    fetch_stock_data.py
    compute_indicators.py
    generate_signals.py
    fetch_fundamentals.py
    analyze_options.py
    fetch_options_chain.py
    angel_auth.py
    ml_predictor.py
    theme.py
```

**Why this separation?** AI/probabilistic reasoning (the agent) only decides what to call. Deterministic, testable Python (the tools) does the actual computation. This makes the system easier to debug and test.

---

## The Two Dashboards

### 1. Equity Dashboard (`dashboard.py`)

The main entry point. You pick a stock and timeframe, and it shows:

- **Candlestick price chart** with EMA overlays and volume bars
- **Three signal cards side-by-side:**
  - Technical Signal (BUY/SELL/HOLD + confidence %)
  - Fundamental Signal (scored on PE, ROE, D/E, growth, analyst targets)
  - ML Signal (Random Forest next-day direction prediction)
- **ATR-based trade setup:** Entry price, Stop Loss, Target
- **Fundamentals panel:** Real data from screener.in (primary) + yfinance (fallback)

### 2. Index Options Dashboard (`pages/index_options.py`)

For NIFTY, BANKNIFTY, MIDCPNIFTY. Shows:

- OI Tornado Chart — visual open interest for CALLs vs PUTs across strikes
- Put-Call Ratio (PCR) and Max Pain
- Recommended option to BUY (CALL or PUT), which strike, which expiry, SL, and target
- Auto-refreshes every 5 minutes

---

## Data Flow (Step by Step)

```
User selects stock + interval + period
        ↓
tools/fetch_stock_data.py
  → Tries Angel One SmartAPI (real-time, requires .env credentials)
  → Falls back to Yahoo Finance if Angel One fails (~15 min delay)
  → Returns: OHLCV DataFrame
        ↓
tools/compute_indicators.py
  → Computes all technical indicators on the DataFrame (pure pandas/numpy)
  → Adds columns: RSI_14, MACD, MACD_signal, MACD_hist, EMA_9/21/50/200,
                  BB_upper/lower/middle/pct, ATR_14, OBV
  → Detects Support & Resistance via swing highs/lows
  → Returns: enriched DataFrame
        ↓
tools/generate_signals.py
  → Each indicator scores the current bar (positive = bullish, negative = bearish)
  → Scores summed → normalized to 0–100 Confidence score
  → Confidence > 60 → BUY | 40–60 → HOLD | < 40 → SELL
  → Returns: {signal, confidence, components, entry, stop_loss, target}
        ↓
(Parallel)
tools/fetch_fundamentals.py  →  Scrapes screener.in + yfinance for PE, ROE, etc.
tools/ml_predictor.py        →  Trains Random Forest on indicator features → up/down prediction
        ↓
dashboard.py
  → Renders everything using Streamlit + Plotly
```

---

## Technical Indicators Explained

| Indicator | What it measures | Bullish signal |
|---|---|---|
| RSI (14) | Momentum. 0–100 scale. | < 30 = oversold → likely bounce |
| MACD (12/26/9) | Trend momentum via two EMAs | MACD line crosses above signal line |
| EMA 9/21/50/200 | Short/medium/long-term trend | Price above all 4 EMAs = strong uptrend |
| Bollinger Bands (20, 2σ) | Volatility range around 20-day MA | Price at lower band = potential reversal |
| Support & Resistance | Key price levels from swing points | Price bouncing off support |
| OBV (On-Balance Volume) | Whether volume confirms price move | Rising OBV with rising price = confirmed |
| ATR (14) | Average True Range = volatility size | Used for SL/target sizing, not for signal |

### Scoring System

Each indicator votes with a score:

| Indicator | Max Bullish | Max Bearish |
|---|---|---|
| RSI | +15 | −15 |
| MACD | +20 | −20 |
| EMA Trend | +20 | −20 |
| Bollinger Bands | +15 | −15 |
| Support/Resistance | +15 | −15 |
| OBV | +15 | −15 |

```
Raw Score  = sum of all scores        (range: roughly −85 to +85)
Confidence = ((Raw Score + 100) / 200) × 100   (normalized to 0–100%)
```

---

## Fundamental Scoring

Pulled from **screener.in** (India-specific, consolidated financials) with yfinance for analyst targets.

| Dimension | Points |
|---|---|
| PE Ratio (lower is better) | 15 |
| ROE (higher = more efficient) | 15 |
| Debt/Equity (lower = safer) | 15 |
| Revenue Growth (YoY) | 15 |
| Profit Margin | 15 |
| Analyst Recommendation + Target Upside | 25 |

**Total: 100 pts.** Grade: Strong (≥65) · Fair (45–64) · Weak (<45)

---

## ML Predictor

Trains a **Random Forest classifier** fresh each time on historical data for the selected stock.

**12 features used:**

| Feature | What it is |
|---|---|
| rsi | RSI value (0–100) |
| macd_hist | MACD histogram (momentum delta) |
| bb_pct | Where price sits in Bollinger Band (0=lower, 1=upper) |
| ema9/21/50/200_dist | % distance of price from each EMA |
| atr_pct | ATR as % of price (volatility measure) |
| vol_change | Day-over-day volume change |
| ret_1d | 1-day return |
| ret_5d | 5-day return |
| obv_slope | Trend slope of OBV (rolling regression) |

**Target:** Will tomorrow's close be higher than today's close? (1=up, 0=down/flat)

**No paid API.** Uses only `scikit-learn` RandomForestClassifier.

---

## Options Logic (Index Options Dashboard)

### How it picks which option to buy

1. Fetch the live options chain from Angel One (OI, LTP, bid/ask for each strike)
2. Compute PCR = total PUT OI / total CALL OI
   - PCR > 1.2 → bullish bias (more puts = protective hedging by big players)
   - PCR < 0.8 → bearish bias (more calls = speculation from bulls)
3. Find Max Pain: the strike where total option sellers lose the least at expiry
4. Run technical signal on the underlying index (same RSI/MACD/EMA pipeline)
5. Choose CALL or PUT based on the signal
6. Strike selection:
   - ATM (At-the-Money) if confidence ≥ 70%
   - 1-OTM (slightly out of the money) if confidence is lower
7. SL/Target:
   - Intraday: SL = −35% of premium, Target = +75%
   - Positional: SL = −40%, Target = +100%

---

## Authentication: Angel One SmartAPI

Credentials needed (in `.env`):

```
ANGEL_API_KEY=
ANGEL_CLIENT_ID=
ANGEL_MPIN=
ANGEL_TOTP_SECRET=
```

`tools/angel_auth.py` handles:
- Singleton login pattern (logs in once, reuses session token)
- TOTP generation via `pyotp` (handles both base32 and hex/UUID format secrets)
- Automatic re-login on session expiry
- Graceful fallback: if credentials are absent, the app uses Yahoo Finance instead

---

## Caching Strategy

| Cache | TTL | Why |
|---|---|---|
| `@st.cache_data` on OHLCV fetch | 5 min | Avoid re-hitting Angel One / yfinance on every UI interaction |
| Angel token lookup | 1h (file: `.tmp/angel_tokens.json`) | `searchScrip` API results don't change |
| NSE equity list | 24h (file: `.tmp/nse_equity.csv`) | The CSV is large; refreshing hourly is wasteful |

---

## Known Limitations (important to communicate)

1. **Not financial advice.** Decision-support only. No backtested proof of profitability.
2. **IV = 0%** — Angel One API doesn't return Implied Volatility directly.
3. **No order placement** — you must execute trades manually on your broker.
4. **15-min delay** when Angel One credentials are absent (yfinance fallback).
5. **OBV slope OTM divergence** — OBV is computed from yfinance volume, which may differ from live Angel One volume.
6. **Random Forest retrains every run** — no saved model; prediction may vary slightly across refreshes.
7. **Plotly category x-axis** — intentional design choice. String date labels used to eliminate weekend/holiday gaps on price charts. `yaxis=dict(range=[-0.5, n-0.5])` fix needed for OI chart due to Plotly 6 numeric-string parsing.

---

## How to Run

```bash
# 1. Activate venv
source .venv/bin/activate

# 2. Fill in credentials
cp .env.example .env
# Edit .env with your Angel One keys

# 3. Run
streamlit run dashboard.py
# Opens at http://localhost:8501
```

Index Options is accessible via the top navigation inside the app.

---

## File Structure Cheat Sheet

```
dashboard.py               → Main Streamlit app (equity deep-dive)
pages/
  index_options.py         → NIFTY/BANKNIFTY options page
  about.py                 → About page

tools/
  angel_auth.py            → Angel One login singleton + TOTP handling
  fetch_angel_ohlcv.py     → Real-time OHLCV via Angel One
  fetch_stock_data.py      → Orchestrator: Angel One → yfinance fallback
  fetch_options_chain.py   → Live options chain (OI, LTP, bid/ask)
  fetch_fundamentals.py    → Scrapes screener.in + yfinance fundamentals
  compute_indicators.py    → Pure pandas: RSI, MACD, EMA, BB, ATR, OBV, S/R
  generate_signals.py      → Scoring engine → BUY/HOLD/SELL + confidence
  analyze_options.py       → PCR, Max Pain, strike selection, SL/target
  ml_predictor.py          → Random Forest next-day direction classifier
  theme.py                 → Plotly/Streamlit dark theme helpers

workflows/
  trading_dashboard.md     → SOP: how to run the system end-to-end

tests/
  test_options_fixes.py    → Unit tests for options chain + signal edge cases

.streamlit/config.toml     → Dark theme + headless mode
.env.example               → Template for credentials
requirements.txt           → All Python dependencies
```

---

## Key Concepts to Explain to Someone

When presenting this project, hit these points:

1. **Why WAT architecture?** Separation of concerns — AI reasons, Python executes. Easy to test tools independently.
2. **Why Angel One + yfinance?** Angel One is real-time but requires credentials. yfinance is free/open but 15-min delayed. Having both means the app works even without an account.
3. **Why score-based signals instead of a single rule?** Markets are noisy. One indicator being bullish while others are bearish is a HOLD — you want consensus, not a single trigger.
4. **Why Random Forest?** Interpretable, works on small datasets, fast to train, no GPU needed. For a personal tool, it's appropriate — not overfit on huge data, not too simple either.
5. **What screener.in is:** An Indian financial data site (free, no API key). The fundamentals tool scrapes its HTML tables directly — PE, ROE, D/E, sales growth.
6. **What PCR and Max Pain mean:** PCR measures put vs call OI balance (institutional hedging sentiment). Max Pain is the strike where option sellers collectively lose least at expiry — markets gravitate toward it.
7. **Why buy-side only?** Short selling and futures carry unlimited downside risk and require margin. This tool is intentionally scoped to defined-risk instruments only.
