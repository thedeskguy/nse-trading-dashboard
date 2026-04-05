# Trading Dashboard Workflow

## Objective
Run the NSE/BSE trading dashboard to analyze Indian stocks and generate BUY/SELL/HOLD signals with technical indicators.

## Prerequisites
- Python 3.10+
- `.venv` exists (run `python3 -m venv .venv` if not)
- Dependencies installed

## Setup (one-time)
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## Run
```bash
source .venv/bin/activate
streamlit run dashboard.py
```
Browser opens at http://localhost:8501

## Tool Sequence
```
tools/fetch_stock_data.py   →  OHLCV DataFrame (yfinance)
tools/compute_indicators.py →  Enriched DataFrame (RSI, MACD, EMA, BB, ATR, OBV, S/R)
tools/generate_signals.py   →  Signal dict (BUY/SELL/HOLD + score + components)
dashboard.py                →  Streamlit UI renders everything
```

## Signal Logic Summary
Each indicator scores ±points, total normalized to 0–100:
- RSI: ±15 (oversold/overbought)
- MACD: ±20 (crossover = ±20, sustained = ±10)
- EMA Trend: ±20 (graduated by # of EMAs price is above)
- Bollinger Bands: ±15 (band touch)
- Support/Resistance: ±15 (proximity to key levels)
- OBV: ±15 (confirmation = ±15, divergence = ±8)

**Thresholds:** BUY > 60 | HOLD 40–60 | SELL < 40

## Known yfinance Constraints
| Interval | Max Lookback | Notes |
|---|---|---|
| 5m / 15m / 30m | 60 days | Use period="1mo" max |
| 1h | ~730 days | Reliable |
| 1d / 1wk | 20+ years | Most reliable |

- NSE tickers: append `.NS` (e.g. `RELIANCE.NS`)
- BSE tickers: append `.BO` (e.g. `RELIANCE.BO`)
- Nifty 50 index: `^NSEI`, Sensex: `^BSESN`
- Special ticker: `BAJAJ-AUTO.NS` (hyphen, not space)
- Intraday data is ~15 minutes delayed
- Dashboard caches data for 5 minutes (click "Refresh" to force reload)

## Edge Cases
- **Empty DataFrame**: ticker not found or market closed (weekend/holiday)
- **NaN indicators**: insufficient history (EMA_200 needs 200+ bars — use period="1y" or longer for daily)
- **BSE `.BO` volume = 0**: zero-volume rows are auto-dropped; use `.NS` for better data quality
- **Rate limits**: ~2000 requests/hour per IP; 5-min cache keeps usage well within limits
