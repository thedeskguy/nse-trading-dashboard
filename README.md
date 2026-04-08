# NSE/BSE Trading Dashboard

A **buy-side only** decision-support tool for Indian market participants. Combines real-time OHLCV data from Angel One SmartAPI, technical analysis, fundamental data, ML price prediction, and options analysis — without placing any orders.

## Dashboards

| Dashboard | File | Purpose |
|---|---|---|
| Index Options | `index_options.py` | Buy CALL or PUT on NIFTY / BANKNIFTY for a specific strike & expiry |
| Equity Scanner | `equity_scanner.py` | Scan Nifty 100 stocks for BUY setups with entry, stop-loss, and target |
| Trading Dashboard | `dashboard.py` | Single-stock deep-dive: OHLCV chart, signals, fundamentals, ML prediction |

**What it does NOT do:** Short selling, futures, intraday scalping, or order placement.

---

## Features

### Equity & Options
- **Real-time OHLCV** — Angel One SmartAPI as primary source (no delay); auto-falls back to Yahoo Finance (~15 min delay) if credentials are missing or the API fails
- **Token lookup cache** — `searchScrip`-based token resolution cached to `.tmp/angel_tokens.json`; no large instrument-master download needed
- **Live options chain** — OI, LTP, bid/ask for NIFTY and BANKNIFTY via Angel One SmartAPI
- **Put-Call Ratio (PCR)** and **Max Pain** computation per expiry
- **OI chart** — visual call/put open interest across strikes
- **Multi-indicator signal engine** — RSI, MACD, EMA (9/21/50/200), Bollinger Bands, Support/Resistance, OBV
- **Confidence score (0–100%)** — composite score mapped to BUY / HOLD / SELL
- **ATR-based entry/SL/target** — stops calibrated to each stock's actual volatility
- **Nifty 100 universe scan** — screens Nifty 50 + Nifty Next 50 simultaneously
- **Any-stock search** — search any NSE equity by symbol via Angel One's `searchScrip`
- **Fundamental analysis** — PE, ROE, D/E, revenue growth, profit margin, analyst targets scored 0–100
- **ML price direction predictor** — Random Forest trained on 12 technical features; predicts next-day up/down

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

### 3. Run the dashboards

```bash
# Index Options dashboard
streamlit run index_options.py --server.port 8504

# Equity Scanner
streamlit run equity_scanner.py --server.port 8505

# Trading Dashboard (single-stock deep-dive)
streamlit run dashboard.py --server.port 8506
```

---

## Project Structure

```
.
├── index_options.py           # Index options dashboard (NIFTY / BANKNIFTY)
├── equity_scanner.py          # Nifty 100 equity scanner
├── dashboard.py               # Single-stock deep-dive dashboard
├── tools/
│   ├── angel_auth.py          # Angel One SmartAPI authentication
│   ├── fetch_angel_ohlcv.py   # Real-time OHLCV via Angel One (with yfinance fallback)
│   ├── fetch_options_chain.py # Options chain data fetcher
│   ├── fetch_stock_data.py    # OHLCV orchestrator (Angel primary → yfinance fallback)
│   ├── compute_indicators.py  # RSI, MACD, EMA, BB, OBV, S/R
│   ├── generate_signals.py    # Scoring engine → BUY/HOLD/SELL
│   ├── analyze_options.py     # PCR, Max Pain, strike selection
│   ├── fetch_fundamentals.py  # Fundamental metrics via yfinance (PE, ROE, D/E, etc.)
│   ├── ml_predictor.py        # Random Forest next-day direction predictor
│   └── theme.py               # Plotly/Streamlit theme config
├── tests/
│   └── test_options_fixes.py  # Unit tests for options chain and signal edge cases
├── workflows/
│   └── trading_dashboard.md   # SOP for running the system
├── assets/
│   └── favicon.svg
├── requirements.txt
├── .env.example
└── SYSTEM_GUIDE.md            # Full explanation of indicators and columns
```

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
