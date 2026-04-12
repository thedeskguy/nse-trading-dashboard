"""
About page content — called by dashboard.py for single-page routing.
"""

import streamlit as st
from tools.theme import page_header


def render_page():
    """Render the About page content (no sidebar needed)."""
    # Hide the sidebar — nothing useful lives there on this page
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] { display: none !important; }
        .main .block-container { padding-left: 2rem !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    page_header("How It Works", "Methodology behind every signal, score, and prediction")

    # ── Section 1 — Technical Analysis ────────────────────────────────────────
    st.header("📊 Technical Analysis Signal")

    st.markdown("""
The technical signal is a **composite score** built by independently evaluating six
indicators on the latest price bar. Each indicator returns a point score; the sum is
normalised to a 0–100 confidence percentage.

**Formula:**
```
Raw Score   = RSI + MACD + EMA Trend + Bollinger Bands + Support/Resistance + OBV
Confidence  = ((Raw Score + 100) / 200) × 100     (clamped 0–100)
```

> Raw Score range: −100 to +100 (worst bearish → strongest bullish)
""")

    st.markdown("#### Indicator Scoring Rules")

    tab_rsi, tab_macd, tab_ema, tab_bb, tab_sr, tab_obv = st.tabs(
        ["RSI", "MACD", "EMA Trend", "Bollinger Bands", "Support / Resistance", "OBV"]
    )

    with tab_rsi:
        st.markdown("**RSI (14-period Relative Strength Index) — max ±15 pts**")
        st.table({
            "RSI Value": ["< 30", "30–40", "40–60", "60–70", "> 70"],
            "Score":     ["+15", "+8", "0", "−8", "−15"],
            "Interpretation": [
                "Oversold — Bullish",
                "Approaching Oversold",
                "Neutral",
                "Approaching Overbought",
                "Overbought — Bearish",
            ],
        })

    with tab_macd:
        st.markdown("**MACD (12/26/9) — max ±20 pts**")
        st.table({
            "Condition": [
                "Bullish crossover (MACD crosses above Signal)",
                "Bearish crossover (MACD crosses below Signal)",
                "MACD above Signal (no fresh cross)",
                "MACD below Signal (no fresh cross)",
                "Equal",
            ],
            "Score": ["+20", "−20", "+10", "−10", "0"],
        })

    with tab_ema:
        st.markdown("**EMA Trend (9 / 21 / 50 / 200) — max ±20 pts**")
        st.markdown("""
    Counts how many EMAs the current price is trading **above**.
    Score normalises to available EMAs (some may be missing for short periods):
    """)
        st.table({
            "EMAs price is above": ["4/4 (all)", "3/4", "2/4", "1/4", "0/4 (none)"],
            "Score": ["+20", "+15", "+10", "−10", "−20"],
        })

    with tab_bb:
        st.markdown("**Bollinger Bands (20-period, 2σ) — max ±15 pts**")
        st.table({
            "Condition": [
                "Price near/at lower band (within 5% of band range)",
                "Price near/at upper band (within 5% of band range)",
                "BB Squeeze (bandwidth narrowing)",
                "Price inside bands",
            ],
            "Score": ["+15", "−15", "0", "0"],
            "Interpretation": [
                "Oversold — potential reversal up",
                "Overbought — potential reversal down",
                "Breakout pending — no directional bias",
                "Neutral",
            ],
        })

    with tab_sr:
        st.markdown("**Support & Resistance — max ±15 pts**")
        st.markdown("""
    Support and resistance levels are computed as recent swing lows/highs from the last
    60 bars using a rolling window approach.
    """)
        st.table({
            "Condition": [
                "Price within 1% of Support",
                "Price within 1% of Resistance",
                "Price 0.5–2% above Support (bounced)",
                "Price below Support (breakdown)",
                "Between S/R levels",
            ],
            "Score": ["+15", "−15", "+10", "−10", "0"],
        })

    with tab_obv:
        st.markdown("**OBV (On-Balance Volume) — max ±15 pts**")
        st.markdown("""
    A 10-period linear regression slope is computed on both OBV and price.
    The slope is normalised by mean OBV (scale-independent).
    """)
        st.table({
            "OBV trend": ["Rising", "Rising", "Falling", "Falling"],
            "Price trend": ["Rising", "Falling", "Falling", "Rising"],
            "Score": ["+15", "+8", "−15", "−8"],
            "Interpretation": [
                "OBV confirming uptrend",
                "Bullish divergence (volume leading price)",
                "OBV confirming downtrend",
                "Bearish divergence (volume leading price)",
            ],
        })

    st.markdown("#### Signal Thresholds")
    col1, col2, col3 = st.columns(3)
    col1.success("**BUY** — Confidence > 60%")
    col2.warning("**HOLD** — Confidence 40–60%")
    col3.error("**SELL** — Confidence < 40%")

    st.markdown("#### Stop Loss & Target (ATR-based)")
    st.markdown("""
Entry levels use **ATR (14-period Average True Range)** calibrated to each stock's
actual volatility — so stops are proportional to how much the stock typically moves,
not a fixed percentage.

```
Stop Loss  = Last Price − 1.5 × ATR14      (for BUY signals)
Target     = Last Price + 3.0 × ATR14      (for BUY signals)
Risk:Reward ratio = 1 : 2
```

For SELL signals the formula is mirrored (SL above price, target below).
For HOLD signals a symmetric ±1.5×ATR zone is shown.
""")

    st.divider()

    # ── Section 2 — Fundamental Analysis ──────────────────────────────────────
    st.header("📋 Fundamental Analysis Signal")

    st.markdown("""
Fundamental data is fetched from two sources:
- **Yahoo Finance** (`yfinance`) — PE, analyst targets, margins, growth rates, beta
- **Screener.in** — Indian-specific data: ROCE, book value, dividend yield, market cap
  (falls back to fill fields that yfinance rate-limits on cloud deployments)

The score is computed on **up to 6 dimensions** (total 100 pts). If a metric is
unavailable, its points default to 0 rather than penalising the stock.
""")

    st.markdown("#### Scoring Dimensions")

    data_fund = {
        "Dimension": [
            "PE Ratio (Trailing)",
            "ROE (Return on Equity)",
            "Debt / Equity",
            "Revenue Growth (YoY)",
            "Net Profit Margin",
            "Analyst View",
        ],
        "Max Points": [15, 15, 15, 15, 15, 25],
        "How scored": [
            "< 15x → 15, 15–25 → 12, 25–40 → 8, > 40 → 2",
            "> 20% → 15, 15–20% → 12, 10–15% → 8, < 10% → 2",
            "< 30 → 15, 30–80 → 10, 80–150 → 5, > 150 → 0",
            "> 20% → 15, 10–20% → 10, 5–10% → 6, 0–5% → 3, < 0 → 0",
            "> 20% → 15, 12–20% → 10, 5–12% → 6, < 5% → 2",
            "Analyst rec BUY → +15, HOLD → +8, SELL → 0; upside > 15% → +10, 0–15% → +5",
        ],
    }
    st.table(data_fund)

    st.markdown("#### Grade")
    g1, g2, g3 = st.columns(3)
    g1.success("**Strong** — Score ≥ 65")
    g2.warning("**Fair** — Score 45–64")
    g3.error("**Weak** — Score < 45")

    st.markdown("#### Fundamental Signal → BUY / HOLD / SELL")
    st.table({
        "Fundamental Score": ["≥ 60", "40–59", "< 40"],
        "Signal": ["BUY", "HOLD", "SELL"],
    })

    st.divider()

    # ── Section 3 — ML Prediction ─────────────────────────────────────────────
    st.header("🤖 ML Price Direction Predictor")

    st.markdown("""
A **Random Forest classifier** (scikit-learn) is trained fresh each session on the
stock's own historical daily OHLCV data — no paid APIs, no pre-trained models.

#### Model architecture
- **Algorithm:** Random Forest (100 trees, max depth 6, min 5 samples per leaf)
- **Training data:** 2 years of daily OHLCV (≈ 500 bars)
- **Target:** Binary — will tomorrow's closing price be **higher** than today's?
  (`1` = UP, `0` = DOWN/flat)
""")

    st.markdown("#### 12 Input Features")

    feat_table = {
        "Feature": [
            "rsi", "macd_hist", "bb_pct",
            "ema9_dist", "ema21_dist", "ema50_dist", "ema200_dist",
            "atr_pct", "vol_change", "ret_1d", "ret_5d", "obv_slope",
        ],
        "Description": [
            "RSI(14) value",
            "MACD histogram (MACD − Signal line)",
            "Bollinger Band %B — price position within the band (0=lower, 1=upper)",
            "(Price − EMA9) / Price — how far price is above/below EMA9",
            "(Price − EMA21) / Price",
            "(Price − EMA50) / Price",
            "(Price − EMA200) / Price",
            "ATR(14) as a fraction of price — normalised volatility",
            "Today's volume vs 10-day average volume (excess volume ratio)",
            "1-day price return",
            "5-day price return",
            "Rolling 10-bar linear regression slope of OBV, normalised by mean OBV",
        ],
    }
    st.table(feat_table)

    st.markdown("""
#### Train / Test split

To avoid **look-ahead bias**, the data is split in **chronological order** (no shuffling):

```
First 80% of days → Training set   (model learns patterns)
Last  20% of days → Test set       (held-out, never seen during training)
```

For 500 bars that means ≈ 400 training days and ≈ 100 test days.

#### Backtest accuracy

The reported **"Backtest Accuracy"** is the percentage of correct UP/DOWN predictions
on the **held-out test set** (the last 20% of dates the model never trained on).

```
Accuracy = (correct predictions on test set) / (total test set days)
```

**Important caveat:** This is in-sample on the same ticker's history. It measures how
well the model's pattern recognition generalises to unseen dates on the *same stock*.
It is **not** a walk-forward simulation across multiple stocks or market regimes.
Typical accuracy for daily direction prediction is 52–58%. Above 60% is notable.

#### Prediction for latest bar

After training, the model predicts the direction for **today's latest close → tomorrow**
using the 12 features computed from today's indicators. Any NaN features (e.g. EMA200
not yet available for new listings) are filled with training-set column means.

The reported **confidence** is the model's `predict_proba` output — the fraction of the
100 decision trees that voted for the predicted direction.

#### Limitations
- Retrained every session (no persistence) — results can vary slightly with new data
- Does not incorporate news, earnings surprises, or macro events
- Short-term signal only — not suitable for multi-week position sizing
- Past accuracy on held-out data does not guarantee future accuracy
""")

    st.divider()

    # ── Section 4 — Combined Signal ───────────────────────────────────────────
    st.header("🔮 Combined Signal")

    st.markdown("""
The **Combined Signal** shown on the Technical tab aggregates all three independent
signals via **majority vote**:

```
Votes = count of BUY / HOLD / SELL across [Technical, Fundamentals, ML]
Combined Signal = whichever label received the most votes (2 or 3 out of 3)
Combined Confidence = average of the three individual confidence values
```

**Example:**
- Technical → BUY (54%)
- Fundamentals → BUY (72%)
- ML → SELL (61%)
- Combined → **BUY** (majority 2/3), avg confidence **62%**

This is a simple ensemble. It is not weighted — each source has equal say.
You should always review the individual signals for context before acting.
""")
