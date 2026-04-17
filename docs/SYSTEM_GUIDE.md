# Trading Dashboard — Complete System Guide

*Version 1.0 · April 2026*

---

## 1. What This System Does

This is a **buy-side only** trading analysis dashboard built on two modules:

| Dashboard | File | Port | Purpose |
|---|---|---|---|
| Index Options | `index_options.py` | 8504 | Buy CALL or PUT on NIFTY / BANKNIFTY for a specific strike & expiry |
| Equity Scanner | `equity_scanner.py` | 8505 | Scan Nifty 100 stocks for BUY setups with entry, stop-loss, and target |

**What it does NOT do:** Short selling, futures, intraday scalping, or order placement. It is a decision-support tool — it tells you *what* to consider buying and *where* to exit, but does not place trades.

---

## 2. Data Sources

| Data | Source | Latency |
|---|---|---|
| NIFTY / BANKNIFTY spot price | Angel One SmartAPI (`ltpData`) | Real-time |
| Options chain (OI, LTP, bid/ask) | Angel One SmartAPI (`getMarketData`) | Real-time |
| Equity OHLCV (daily candles) | Yahoo Finance (`yfinance`) | ~15 min delay |
| Instrument token master | Angel One public JSON | Cached 1 hr |

**Why two sources?** Angel One provides real-time options data (critical for OI, premiums) but does not provide clean equity OHLCV for technical analysis. Yahoo Finance covers all NSE equities with full historical data, which is what the signal engine needs.

---

## 3. Technical Indicators Explained

All indicators are computed on **daily candles** (closing price unless stated). Each indicator is scored independently and the scores are combined.

### 3.1 RSI — Relative Strength Index (14-period)

**What it measures:** How fast and how much the price has moved recently. Identifies overbought and oversold conditions.

**Formula:** `RSI = 100 − (100 / (1 + RS))` where RS = Average Gain / Average Loss over 14 days.

**Range:** 0 to 100.

| RSI Value | Interpretation | Score |
|---|---|---|
| < 30 | Oversold — price likely to bounce up | +15 |
| 30–40 | Approaching oversold — mild bullish | +8 |
| 40–60 | Neutral zone — no strong signal | 0 |
| 60–70 | Approaching overbought — mild bearish | −8 |
| > 70 | Overbought — price likely to pull back | −15 |

**Why 14 periods?** The default RSI(14) is used by the majority of institutional desks and is the most widely watched. It balances sensitivity vs. noise.

---

### 3.2 MACD — Moving Average Convergence Divergence (12/26/9)

**What it measures:** Momentum and trend direction by comparing two exponential moving averages.

**Three lines computed:**
- **MACD line** = EMA(12) − EMA(26) — fast momentum
- **Signal line** = EMA(9) of MACD — smoother trigger
- **Histogram** = MACD − Signal — momentum acceleration

| Condition | Interpretation | Score |
|---|---|---|
| MACD crosses above Signal (today) | Bullish crossover — strong buy signal | +20 |
| MACD crosses below Signal (today) | Bearish crossover — strong sell signal | −20 |
| MACD above Signal (no fresh cross) | Uptrend in progress | +10 |
| MACD below Signal (no fresh cross) | Downtrend in progress | −10 |
| MACD = Signal | No clear direction | 0 |

**Why crossovers score highest?** A crossover is the *moment* momentum shifts — the most actionable point in the trend.

---

### 3.3 EMA Trend (9 / 21 / 50 / 200-period)

**What it measures:** Where the current price stands relative to four key moving averages. Each EMA represents a different timeframe of trend.

| EMA | Timeframe | Used by |
|---|---|---|
| EMA 9 | Very short-term (2 weeks) | Day traders, swing traders |
| EMA 21 | Short-term (1 month) | Swing traders |
| EMA 50 | Medium-term (2.5 months) | Position traders |
| EMA 200 | Long-term (1 year) | Institutional benchmark |

**Scoring:** Count how many EMAs the price is above (0–4):

| EMAs Above | Score | Signal |
|---|---|---|
| 4 / 4 | +20 | Strong Bullish |
| 3 / 4 | +15 | Bullish |
| 2 / 4 | +10 | Mildly Bullish |
| 1 / 4 | −10 | Mildly Bearish |
| 0 / 4 | −20 | Strong Bearish |

**Key level — EMA 200:** Price crossing above/below EMA 200 is widely watched as a bull/bear market signal for large-caps.

---

### 3.4 Bollinger Bands (20-period, 2 standard deviations)

**What it measures:** Volatility envelope around price. When price approaches the bands it signals potential reversal; when bands narrow it signals a breakout is coming.

**Three bands:**
- **Upper band** = 20-day SMA + 2 × standard deviation
- **Middle band** = 20-day SMA (the mean)
- **Lower band** = 20-day SMA − 2 × standard deviation

Statistically, ~95% of all closes should be *inside* the bands.

| Condition | Interpretation | Score |
|---|---|---|
| Price near/at lower band | Oversold — likely bounce | +15 |
| Price near/at upper band | Overbought — likely pullback | −15 |
| Bands narrowing (squeeze) | Volatility contraction — breakout imminent | 0 (watch) |
| Price inside bands | Normal range | 0 |

**BB% (Percent B):** Shown in the dashboard. 0 = at lower band, 1 = at upper band, 0.5 = at midline.

---

### 3.5 Support & Resistance

**What it measures:** Price levels where buying or selling has historically been concentrated. Price tends to stall or reverse at these levels.

**How calculated:**
1. Take the last 50 daily candles
2. Identify swing highs (local peaks, looking 5 bars each side) → resistance candidates
3. Identify swing lows (local troughs, looking 5 bars each side) → support candidates
4. Cluster levels within 0.5% of each other (nearby levels are the "same zone")
5. Pick the nearest resistance above price and nearest support below price

| Condition | Interpretation | Score |
|---|---|---|
| Price within 1% of support | Near support — likely to bounce | +15 |
| Price within 1% of resistance | Near resistance — likely to stall | −15 |
| Price bounced 0.5–2% above support | Confirmed support bounce | +10 |
| Price broke below support | Support failed — bearish | −10 |
| Price between S/R | No actionable signal | 0 |

---

### 3.6 OBV — On-Balance Volume

**What it measures:** Whether volume is flowing *into* or *out of* a stock. Volume should confirm price moves — if price rises on high volume and falls on low volume, the trend is healthy.

**Formula:**
- If today's close > yesterday's: add today's volume to OBV
- If today's close < yesterday's: subtract today's volume from OBV

**How scored:** Compare OBV slope vs. price slope over the last 10 days using linear regression.

| Condition | Interpretation | Score |
|---|---|---|
| OBV rising + price rising | Volume confirms uptrend | +15 |
| OBV falling + price falling | Volume confirms downtrend | −15 |
| OBV rising + price falling | Bullish divergence — smart money accumulating | +8 |
| OBV falling + price rising | Bearish divergence — distribution phase | −8 |

**Why OBV matters:** Price can be manipulated in the short term, but volume is harder to fake. OBV divergences often precede major reversals.

---

## 4. Scoring System — How the Signal Is Generated

### 4.1 Raw Score

Each indicator contributes a score. All six are summed:

```
Raw Score = RSI + MACD + EMA Trend + Bollinger + Support/Resistance + OBV
```

**Theoretical range:** −85 to +85
- Maximum bullish: RSI(+15) + MACD(+20) + EMA(+20) + BB(+15) + S/R(+15) = +85
- Maximum bearish: −85

### 4.2 Normalisation to 0–100 Confidence

```
Confidence = ((Raw Score + 100) / 200) × 100
```

This maps −100 → 0%, 0 → 50%, +100 → 100%.

### 4.3 Signal Classification

| Confidence | Signal | Action |
|---|---|---|
| > 60% | BUY | Consider buying CALL (index) or stock |
| 40–60% | HOLD | Conflicting signals — wait |
| < 40% | SELL | Consider buying PUT (index) or avoid stock |

**Important:** The equity scanner only shows BUY signals. HOLD and SELL are filtered out.

---

## 5. Index Options Dashboard — Column Meanings

### 5.1 Summary Row

| Field | Meaning |
|---|---|
| Signal | BUY (bullish) or SELL (bearish) based on underlying index trend |
| Confidence | 0–100% — how strongly the indicators agree |
| Direction | Bullish = indicators point up; Bearish = point down |
| PCR | Put-Call Ratio (see section 6) |
| Max Pain | Strike price where option buyers collectively lose the most |

### 5.2 Recommendation Card

| Field | How Calculated |
|---|---|
| **Strike** | ATM strike (rounded to nearest interval: 50 for NIFTY, 100 for BANKNIFTY) if confidence ≥ 70%; 1 strike OTM if confidence 60–70% (positional only) |
| **Expiry** | Intraday = selected expiry; Positional = next expiry after selected |
| **Premium (LTP)** | Last traded price of the option contract from Angel One live feed |
| **Bid / Ask** | Best buy and sell price in the order book |
| **IV (Implied Volatility)** | Currently 0% — Angel One `getMarketData` does not return IV directly; requires Black-Scholes computation (planned) |
| **Stop Loss** | Intraday: premium × 65% (exit at 35% loss). Positional: premium × 60% (exit at 40% loss) |
| **Target** | Intraday: premium × 175% (75% gain). Positional: premium × 200% (100% gain, i.e. double) |
| **Capital / Lot** | Premium × Lot Size (NIFTY = 75, BANKNIFTY = 30) |
| **Max Loss / Lot** | (Premium − Stop Loss) × Lot Size |
| **Max Profit / Lot** | (Target − Premium) × Lot Size |
| **Reward : Risk** | Max Profit / Max Loss per lot |

### 5.3 SL & Target Rationale

| Style | SL % | Target % | Logic |
|---|---|---|---|
| Intraday | −35% of premium | +75% of premium | Theta decay is aggressive near expiry — tight SL, reasonable target |
| Positional | −40% of premium | +100% of premium (2×) | More time means wider swings are acceptable; risk-reward should be at least 1:2 |

If signal confidence ≥ 70%, the positional target increases to +100%. If 60–70%, stays at +80%.

---

## 6. Put-Call Ratio (PCR)

**Formula:** `PCR = Total PUT Open Interest / Total CALL Open Interest` for the selected expiry.

**Interpretation:**

| PCR | What it means | Dashboard signal |
|---|---|---|
| > 1.2 | More puts being *written* than calls → market makers expect the index to stay up or rise | Bullish |
| 0.8–1.2 | Balanced positioning | Neutral |
| < 0.8 | More calls being *written* → market makers expect the index to fall | Bearish |

**Counterintuitive logic:** PCR measures option *writers* (sellers), not buyers. A high PCR means put sellers (who profit if market stays up) outnumber call sellers — a bullish contrarian signal.

---

## 7. Max Pain

**What it is:** The strike price at which all open option contracts would expire worthless, causing maximum aggregate loss to option *buyers*.

**How calculated:**
1. For every possible expiry strike, calculate total payout if index expires at that strike
2. Sum all ITM call losses + all ITM put losses
3. The strike with the minimum total payout = Max Pain

**Why it matters:** Market makers and large option sellers have an incentive to pin the index near Max Pain at expiry. This level acts as a gravitational pull in the last 1–2 days before expiry. Do not use Max Pain for longer timeframes.

---

## 8. Open Interest Chart

**X-axis:** Open Interest in number of contracts (CE = positive, right; PE = negative, left)
**Y-axis:** Strike prices
**ATM line:** Dashed white line at the nearest-to-spot strike

**What to look for:**

| Pattern | Meaning |
|---|---|
| High CE OI at a strike above spot | Strong resistance — call writers defending that level |
| High PE OI at a strike below spot | Strong support — put writers defending that level |
| CE OI >> PE OI | More calls written → bearish tilt from market makers |
| PE OI >> CE OI | More puts written → bullish tilt from market makers |
| Sudden OI buildup overnight | Institutional positioning — usually directional |

---

## 9. Equity Scanner — Column Meanings

| Column | Meaning |
|---|---|
| **Stock** | Company name |
| **LTP** | Last traded price (Yahoo Finance, ~15 min delay) |
| **Signal** | BUY only shown — HOLD/SELL filtered out |
| **Confidence** | 0–100% composite indicator score |
| **Entry** | LTP at the time of scan — buy near this price |
| **Stop Loss** | LTP − (1.5 × ATR). Exit if price falls here |
| **Target** | LTP + (3.0 × ATR). Book profit here |
| **R:R** | Reward-to-Risk ratio = (Target−Entry) / (Entry−StopLoss). Minimum 1.5:1 shown |
| **RSI** | Current RSI(14) value |
| **ATR** | Current ATR(14) in rupees — measures daily volatility range |

### 9.1 Entry, Stop Loss, Target on Equity

```
ATR = Average True Range over 14 days (average daily price range)

Stop Loss = Entry Price − (1.5 × ATR)
Target    = Entry Price + (3.0 × ATR)
R:R Ratio = 3.0 × ATR / 1.5 × ATR = 2.0 (always 2:1)
```

ATR-based exits automatically adjust for each stock's volatility. A high-volatility stock like Tata Motors gets a wider SL than a stable stock like ITC.

---

## 10. ATR — Average True Range

**What it is:** The average of the *true range* over 14 days. True range = max of:
- High − Low (day's range)
- |High − Previous Close| (gap up)
- |Low − Previous Close| (gap down)

**Why ATR for exits?** Fixed-percentage stops (e.g. "exit at −2%") don't account for each stock's natural volatility. A 2% move in Reliance is noise; a 2% move in a mid-cap could be a breakdown. ATR gives a stop that is calibrated to how much that specific stock *normally* moves.

---

## 11. Stock Universe

The equity scanner covers **Nifty 100 = Nifty 50 + Nifty Next 50**. All constituents have market cap > ₹4,000 crore (most are ₹50,000–₹20,00,000 crore).

Additionally, you can **search any NSE stock** via the sidebar search box. The search uses Angel One's `searchScrip` API and filters for `-EQ` suffix (equity instruments only). Type the NSE symbol (e.g. `ZOMATO`, `PAYTM`) for best results.

---

## 12. Backtesting Status

| Module | Backtested? | Details |
|---|---|---|
| Signal scoring (equity) | **Partial** | Scoring weights (RSI, MACD, EMA, BB, OBV, S/R) are based on widely published research and practitioner consensus, not on a formal backtest over this specific codebase. The system has not run a historical walk-forward simulation on Nifty 100 data. |
| Strike selection | **No** | ATM vs. 1-OTM selection for intraday vs. positional is rule-of-thumb, not optimised. |
| SL/Target percentages | **No** | 35% SL / 75% target for intraday and 40% SL / 100% target for positional are common practitioner defaults. They have not been backtested on historical NSE options data. |
| PCR threshold | **Partial** | PCR >1.2 = bullish, <0.8 = bearish are standard NSE options market thresholds used by most data providers. |
| Max Pain | **No** | Max Pain is computed mathematically correctly but its predictive value varies by market regime. |

### What a formal backtest would require

To properly backtest this system you would need:

1. **Historical daily OHLCV** for Nifty 100 stocks (at least 5 years) — available via Yahoo Finance
2. **Historical options chain snapshots** (OI, premiums, expiry dates) — available from NSE bhavcopy archives or paid data providers
3. **Walk-forward testing:** Generate signals on day D, simulate entry on day D+1 open, apply SL/target rules, record outcome
4. **Metrics to compute:** Win rate, average R:R achieved, max drawdown, Sharpe ratio, comparison to Nifty 50 buy-and-hold

This is **not currently implemented** in the codebase. The system provides real-time analysis based on proven indicator logic, but the specific parameter values (scoring weights, SL%, target%, confidence thresholds) should be treated as starting points and validated with your own trading journal over time.

---

## 13. Limitations & Risk Disclosures

1. **Not financial advice.** This is a decision-support tool. Always apply your own judgement.
2. **No execution.** The dashboard does not place orders. You must execute on your own platform.
3. **Equity data is delayed ~15 min** due to Yahoo Finance. Do not use LTP from the scanner as an intraday entry price — check the live feed on your broker.
4. **Options data is real-time** via Angel One, but only during market hours. Overnight the data shows last-session values.
5. **IV is not computed.** Angel One's `getMarketData` does not return IV directly. The IV column shows 0%. A proper Black-Scholes calculation using spot, strike, expiry, and risk-free rate is needed — not yet implemented.
6. **Backtest gap.** See Section 12. Do not risk capital based purely on this system without tracking its accuracy in a paper-trading journal first.
7. **Angel One API rate limits.** The search feature may return "rate limit" errors if queries come too fast. The scanner uses 5-minute caching to avoid this.

---

## 14. Planned Improvements

- [ ] Compute IV using Black-Scholes from first principles
- [ ] Backtest signal scoring over 3-year Nifty 100 history
- [ ] Add options Greeks (Delta, Theta, Gamma) per recommendation
- [ ] Email/WhatsApp alert when a high-confidence BUY signal appears
- [ ] Add 15-min / 1-hour intraday signal mode for equity scanner
- [ ] Portfolio tracker — log entries and track open positions

---

*Built with: Python · Streamlit · Angel One SmartAPI · Yahoo Finance · pandas-ta · Plotly*
