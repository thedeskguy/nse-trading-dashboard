"""
NSE/BSE Trading Dashboard
Real-time technical analysis with BUY/SELL/HOLD signals.
Run: streamlit run dashboard.py
"""

import sys
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

sys.path.insert(0, ".")
from tools.fetch_stock_data import fetch_ohlcv, VALID_COMBOS
from tools.compute_indicators import compute_all
from tools.generate_signals import generate_signal
from tools.analyze_options import recommend_option
from tools.theme import inject_css, signal_badge, page_header
from tools.fetch_fundamentals import fetch_fundamentals, score_fundamentals
from tools.ml_predictor import train_and_predict

# ── Nifty 50 tickers ──────────────────────────────────────────────────────────
NIFTY50 = {  # noqa: E501
    "Reliance Industries":    "RELIANCE.NS",
    "TCS":                    "TCS.NS",
    "HDFC Bank":              "HDFCBANK.NS",
    "Infosys":                "INFY.NS",
    "ICICI Bank":             "ICICIBANK.NS",
    "Hindustan Unilever":     "HINDUNILVR.NS",
    "ITC":                    "ITC.NS",
    "State Bank of India":    "SBIN.NS",
    "Bajaj Finance":          "BAJFINANCE.NS",
    "Bharti Airtel":          "BHARTIARTL.NS",
    "Kotak Mahindra Bank":    "KOTAKBANK.NS",
    "L&T":                    "LT.NS",
    "HCL Technologies":       "HCLTECH.NS",
    "Asian Paints":           "ASIANPAINT.NS",
    "Axis Bank":              "AXISBANK.NS",
    "Maruti Suzuki":          "MARUTI.NS",
    "Sun Pharma":             "SUNPHARMA.NS",
    "Titan Company":          "TITAN.NS",
    "UltraTech Cement":       "ULTRACEMCO.NS",
    "NTPC":                   "NTPC.NS",
    "Power Grid":             "POWERGRID.NS",
    "Wipro":                  "WIPRO.NS",
    "Tech Mahindra":          "TECHM.NS",
    "Nestle India":           "NESTLEIND.NS",
    "Bajaj Auto":             "BAJAJ-AUTO.NS",
    "Hindalco":               "HINDALCO.NS",
    "Tata Steel":             "TATASTEEL.NS",
    "Tata Motors":            "TATAMOTORS.NS",
    "Grasim Industries":      "GRASIM.NS",
    "IndusInd Bank":          "INDUSINDBK.NS",
    "JSW Steel":              "JSWSTEEL.NS",
    "ONGC":                   "ONGC.NS",
    "Coal India":             "COALINDIA.NS",
    "Cipla":                  "CIPLA.NS",
    "Dr. Reddy's":            "DRREDDY.NS",
    "Divi's Labs":            "DIVISLAB.NS",
    "Eicher Motors":          "EICHERMOT.NS",
    "Hero MotoCorp":          "HEROMOTOCO.NS",
    "Mahindra & Mahindra":    "M&M.NS",
    "Tata Consumer":          "TATACONSUM.NS",
    "Adani Ports":            "ADANIPORTS.NS",
    "Apollo Hospitals":       "APOLLOHOSP.NS",
    "Britannia":              "BRITANNIA.NS",
    "Bajaj Finserv":          "BAJAJFINSV.NS",
    "SBI Life Insurance":     "SBILIFE.NS",
    "HDFC Life":              "HDFCLIFE.NS",
    "UPL":                    "UPL.NS",
    "Shree Cement":           "SHREECEM.NS",
    "Nifty 50 Index":         "^NSEI",
    "Sensex Index":           "^BSESN",
}

# ── Nifty Next 50 + other popular stocks ──────────────────────────────────────
OTHER_STOCKS = {
    # Nifty Next 50
    "Adani Enterprises":      "ADANIENT.NS",
    "Adani Green Energy":     "ADANIGREEN.NS",
    "Adani Total Gas":        "ATGL.NS",
    "Ambuja Cements":         "AMBUJACEM.NS",
    "AU Small Finance Bank":  "AUBANK.NS",
    "Berger Paints":          "BERGEPAINT.NS",
    "Bharat Electronics":     "BEL.NS",
    "Cholamandalam Finance":  "CHOLAFIN.NS",
    "Colgate-Palmolive":      "COLPAL.NS",
    "DLF":                    "DLF.NS",
    "Godrej Consumer":        "GODREJCP.NS",
    "Havells India":          "HAVELLS.NS",
    "HDFC AMC":               "HDFCAMC.NS",
    "Indian Oil Corp":        "IOC.NS",
    "Info Edge (Naukri)":     "NAUKRI.NS",
    "Interglobe Aviation":    "INDIGO.NS",
    "Jindal Steel":           "JINDALSTEL.NS",
    "Lupin":                  "LUPIN.NS",
    "Marico":                 "MARICO.NS",
    "Muthoot Finance":        "MUTHOOTFIN.NS",
    "Page Industries":        "PAGEIND.NS",
    "Pidilite Industries":    "PIDILITIND.NS",
    "Piramal Enterprises":    "PEL.NS",
    "Punjab National Bank":   "PNB.NS",
    "Siemens India":          "SIEMENS.NS",
    "SRF Ltd":                "SRF.NS",
    "Torrent Pharma":         "TORNTPHARM.NS",
    "Trent":                  "TRENT.NS",
    "Vedanta":                "VEDL.NS",
    "Voltas":                 "VOLTAS.NS",
    # Banking & Finance
    "Bank of Baroda":         "BANKBARODA.NS",
    "Canara Bank":            "CANBK.NS",
    "Federal Bank":           "FEDERALBNK.NS",
    "IDFC First Bank":        "IDFCFIRSTB.NS",
    "RBL Bank":               "RBLBANK.NS",
    "Yes Bank":               "YESBANK.NS",
    # IT & Tech
    "Coforge":                "COFORGE.NS",
    "LTIMindtree":            "LTIM.NS",
    "Mphasis":                "MPHASIS.NS",
    "Persistent Systems":     "PERSISTENT.NS",
    # Auto & Infra
    "Ashok Leyland":          "ASHOKLEY.NS",
    "Bharat Forge":           "BHARATFORG.NS",
    "Cummins India":          "CUMMINSIND.NS",
    "Escorts Kubota":         "ESCORTS.NS",
    "IRB Infrastructure":     "IRB.NS",
    "Tata Power":             "TATAPOWER.NS",
    "Torrent Power":          "TORNTPOWER.NS",
    # Pharma & Healthcare
    "Alkem Laboratories":     "ALKEM.NS",
    "Biocon":                 "BIOCON.NS",
    "Ipca Laboratories":      "IPCALAB.NS",
    "Mankind Pharma":         "MANKIND.NS",
    "Max Healthcare":         "MAXHEALTH.NS",
    # Consumption & Retail
    "Avenue Supermarts (DMart)": "DMART.NS",
    "Jubilant FoodWorks":     "JUBLFOOD.NS",
    "Oberoi Realty":          "OBEROIRLTY.NS",
    "Polycab India":          "POLYCAB.NS",
    "Eternal":                 "ETERNAL.NS",
    # PSU & Energy
    "BPCL":                   "BPCL.NS",
    "GAIL":                   "GAIL.NS",
    "HPCL":                   "HINDPETRO.NS",
    "NHPC":                   "NHPC.NS",
    "Oil India":              "OIL.NS",
}

STOCK_UNIVERSES = {
    "Nifty 50": NIFTY50,
    "Nifty Next 50 & Others": OTHER_STOCKS,
}

SIGNAL_COLORS = {"BUY": "#00C851", "SELL": "#ff4444", "HOLD": "#ffbb33"}


# ── Data fetching (cached 60s for intraday, 5min for daily) ───────────────────
@st.cache_data(ttl=60)
def load_data(ticker: str, interval: str, period: str):
    df = fetch_ohlcv(ticker, interval=interval, period=period)
    df = compute_all(df)
    return df


# ── Chart builders ─────────────────────────────────────────────────────────────
def _x_labels(df: pd.DataFrame) -> list:
    """String x-axis labels so Plotly uses a categorical axis — no weekend/holiday gaps."""
    idx = df.index
    try:
        if len(idx) > 0 and (idx[0].hour != 0 or idx[0].minute != 0):
            return [ts.strftime('%b %d %H:%M') for ts in idx]
    except AttributeError:
        pass
    return [ts.strftime('%b %d') if hasattr(ts, 'strftime') else str(ts) for ts in idx]


def build_price_chart(df: pd.DataFrame, support, resistance) -> go.Figure:
    fig = go.Figure()
    xlabels = _x_labels(df)

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=xlabels, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        name="Price", increasing_line_color="#26a69a", decreasing_line_color="#ef5350",
    ))

    # Bollinger Bands (shaded)
    if "BB_upper" in df.columns:
        fig.add_trace(go.Scattergl(
            x=xlabels, y=df["BB_upper"], name="BB Upper",
            line=dict(color="rgba(150,150,255,0.5)", width=1), showlegend=True,
        ))
        fig.add_trace(go.Scattergl(
            x=xlabels, y=df["BB_lower"], name="BB Lower",
            line=dict(color="rgba(150,150,255,0.5)", width=1),
            fill="tonexty", fillcolor="rgba(150,150,255,0.07)", showlegend=True,
        ))

    # EMAs
    ema_colors = {"EMA_9": "#FFD700", "EMA_21": "#FF8C00", "EMA_50": "#00BFFF", "EMA_200": "#FF69B4"}
    for col, color in ema_colors.items():
        if col in df.columns:
            fig.add_trace(go.Scattergl(
                x=xlabels, y=df[col], name=col.replace("_", " "),
                line=dict(color=color, width=1.2),
            ))

    # Support / Resistance
    if support:
        fig.add_hline(y=support, line_dash="dot", line_color="#00C851",
                      annotation_text=f"Support ₹{support:.2f}", annotation_position="right")
    if resistance:
        fig.add_hline(y=resistance, line_dash="dot", line_color="#ff4444",
                      annotation_text=f"Resistance ₹{resistance:.2f}", annotation_position="right")

    fig.update_layout(
        title="Price Chart", xaxis_rangeslider_visible=False,
        height=480, template="plotly_dark", legend=dict(orientation="h", y=1.02),
        margin=dict(l=0, r=0, t=40, b=0),
        dragmode="pan",
        uirevision="price",
        xaxis=dict(type="category", fixedrange=False, nticks=7, tickangle=0),
        yaxis=dict(fixedrange=False),
        transition=dict(duration=0, easing="linear"),
    )
    return fig


def build_rsi_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    col = "RSI_14"
    if col not in df.columns:
        return fig

    rsi = df[col]
    colors = ["#00C851" if v < 30 else "#ff4444" if v > 70 else "#888" for v in rsi]

    fig.add_trace(go.Scattergl(
        x=_x_labels(df), y=rsi, name="RSI(14)",
        line=dict(color="#7B68EE", width=1.5),
    ))
    # Overbought/oversold shading
    fig.add_hrect(y0=70, y1=100, fillcolor="rgba(255,68,68,0.1)", line_width=0)
    fig.add_hrect(y0=0, y1=30,  fillcolor="rgba(0,200,81,0.1)",  line_width=0)
    fig.add_hline(y=70, line_dash="dash", line_color="rgba(255,68,68,0.6)", line_width=1)
    fig.add_hline(y=30, line_dash="dash", line_color="rgba(0,200,81,0.6)",  line_width=1)
    fig.add_hline(y=50, line_dash="dot",  line_color="rgba(150,150,150,0.4)", line_width=1)

    fig.update_layout(
        title="RSI (14)", height=200, template="plotly_dark",
        yaxis=dict(range=[0, 100], fixedrange=False),
        xaxis=dict(type="category", fixedrange=False, nticks=7, tickangle=0),
        dragmode="pan",
        uirevision="rsi",
        margin=dict(l=0, r=0, t=40, b=0), showlegend=False,
        transition=dict(duration=0, easing="linear"),
    )
    return fig


def build_macd_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if "MACD" not in df.columns:
        return fig

    hist = df["MACD_hist"]
    bar_colors = ["#00C851" if v >= 0 else "#ef5350" for v in hist.fillna(0)]
    xlabels = _x_labels(df)

    fig.add_trace(go.Bar(
        x=xlabels, y=hist, name="Histogram",
        marker_color=bar_colors, opacity=0.7,
    ))
    fig.add_trace(go.Scattergl(
        x=xlabels, y=df["MACD"], name="MACD",
        line=dict(color="#2196F3", width=1.5),
    ))
    fig.add_trace(go.Scattergl(
        x=xlabels, y=df["MACD_signal"], name="Signal",
        line=dict(color="#FF9800", width=1.5),
    ))
    fig.add_hline(y=0, line_color="rgba(150,150,150,0.4)", line_width=1)

    fig.update_layout(
        title="MACD (12, 26, 9)", height=220, template="plotly_dark",
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(orientation="h", y=1.05),
        dragmode="pan",
        uirevision="macd",
        xaxis=dict(type="category", fixedrange=False, nticks=7, tickangle=0),
        yaxis=dict(fixedrange=False),
        transition=dict(duration=0, easing="linear"),
    )
    return fig


def build_volume_obv_chart(df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    xlabels = _x_labels(df)

    vol_colors = [
        "#26a69a" if df["Close"].iloc[i] >= df["Open"].iloc[i] else "#ef5350"
        for i in range(len(df))
    ]
    fig.add_trace(go.Bar(
        x=xlabels, y=df["Volume"], name="Volume",
        marker_color=vol_colors, opacity=0.7,
    ), secondary_y=False)

    if "OBV" in df.columns:
        fig.add_trace(go.Scattergl(
            x=xlabels, y=df["OBV"], name="OBV",
            line=dict(color="#E040FB", width=1.5),
        ), secondary_y=True)

    fig.update_layout(
        title="Volume + OBV", height=220, template="plotly_dark",
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(orientation="h", y=1.05),
        dragmode="pan",
        uirevision="volume",
        xaxis=dict(type="category", fixedrange=False, nticks=7, tickangle=0),
        yaxis=dict(fixedrange=False),
        transition=dict(duration=0, easing="linear"),
    )
    fig.update_yaxes(title_text="Volume", secondary_y=False)
    fig.update_yaxes(title_text="OBV", secondary_y=True)
    return fig


def render_signal_badge(signal: str, confidence: int) -> None:
    st.markdown(signal_badge(signal, confidence), unsafe_allow_html=True)


def render_indicator_table(components: dict) -> None:
    rows = []
    for name, v in components.items():
        pts = v["points"]
        arrow = "▲" if pts > 0 else ("▼" if pts < 0 else "—")
        rows.append({
            "Indicator": name,
            "Value": str(v["value"]),
            "Signal": v["signal"],
            "Score": f"{arrow} {pts:+d}",
        })
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


# ── Options tab helpers ────────────────────────────────────────────────────────

@st.cache_data(ttl=180)   # 3-min cache for options (more time-sensitive)
def load_options(symbol: str):
    return recommend_option(symbol, style="both")


def render_option_card(style_label: str, rec: dict, color: str) -> None:
    """Render a single intraday or positional option recommendation card."""
    if not rec or "error" in rec:
        st.warning(rec.get("error", "No recommendation available."))
        return

    opt_color = "#00C851" if rec["option_type"] == "CALL" else "#FF6B6B"
    st.markdown(
        f"""
        <div style="border:2px solid {opt_color}; border-radius:12px; padding:16px; margin-bottom:8px;">
            <div style="font-size:1.1rem; font-weight:700; color:{opt_color};">
                BUY {rec['option_type']} — {style_label}
            </div>
            <div style="font-size:1.4rem; font-weight:800; margin:4px 0;">
                {rec['option']}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Entry Premium", f"₹{rec['premium']}")
    c2.metric(f"Stop Loss  (-{rec['sl_pct']}%)", f"₹{rec['stop_loss']}", delta=f"-₹{rec['sl_points']}", delta_color="inverse")
    c3.metric(f"Target  (+{rec['target_pct']}%)", f"₹{rec['target']}", delta=f"+₹{rec['target_points']}", delta_color="normal")
    c4.metric("IV", f"{rec['iv']:.1f}%")

    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Lot Size", str(rec["lot_size"]))
    d2.metric("Capital / Lot", f"₹{rec['capital_1_lot']:,.0f}")
    d3.metric("Max Loss / Lot", f"₹{rec['max_loss_1_lot']:,.0f}")
    d4.metric("Max Profit / Lot", f"₹{rec['max_profit_1_lot']:,.0f}")


def render_options_chain_table(chain_df: pd.DataFrame, spot: float, expiry: str, symbol: str, n_strikes: int = 10) -> None:
    """Show ATM ± n_strikes rows of the options chain."""
    from tools.fetch_options_chain import get_nearest_atm_strike, STRIKE_INTERVALS
    atm = get_nearest_atm_strike(spot, symbol)
    interval = STRIKE_INTERVALS.get(symbol, 50)
    lo = atm - interval * n_strikes
    hi = atm + interval * n_strikes

    df = chain_df[(chain_df["expiry"] == expiry) & chain_df["strike"].between(lo, hi)].copy()
    if df.empty:
        st.info("No chain data for selected expiry.")
        return

    df = df[["strike", "CE_ltp", "CE_iv", "CE_oi", "CE_volume", "PE_ltp", "PE_iv", "PE_oi", "PE_volume"]]
    df.columns = ["Strike", "CE LTP", "CE IV%", "CE OI", "CE Vol", "PE LTP", "PE IV%", "PE OI", "PE Vol"]

    def highlight_atm(row):
        if row["Strike"] == atm:
            return ["background-color: rgba(255,215,0,0.15)"] * len(row)
        return [""] * len(row)

    styled = df.style.apply(highlight_atm, axis=1).format({
        "CE LTP": "₹{:.2f}", "PE LTP": "₹{:.2f}",
        "CE IV%": "{:.1f}", "PE IV%": "{:.1f}",
    })
    st.dataframe(styled, width="stretch", hide_index=True)


# ── Fundamentals + ML cache wrappers ──────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_fundamentals(ticker: str) -> dict:
    return fetch_fundamentals(ticker)


@st.cache_data(ttl=300)
def load_prediction(ticker: str, period: str):
    df = fetch_ohlcv(ticker, interval="1d", period=period if period in ["1y", "2y", "5y"] else "2y")
    df = compute_all(df)
    return train_and_predict(df)


# ── Fundamentals render ────────────────────────────────────────────────────────
def render_fundamentals(ticker: str, last_price: float, preloaded_data=None, preloaded_result=None) -> None:
    if preloaded_data is not None:
        data = preloaded_data
        result = preloaded_result
    else:
        with st.spinner("Loading fundamental data…"):
            data = load_fundamentals(ticker)
        result = score_fundamentals(data, current_price=last_price)
    score = result["score"]
    grade = result["grade"]
    breakdown = result["breakdown"]

    grade_color = {"Strong": "#00C851", "Fair": "#ffbb33", "Weak": "#ff4444"}[grade]
    st.markdown(
        f"""
        <div style="background:{grade_color}18; border:2px solid {grade_color};
                    border-radius:12px; padding:16px 24px; margin-bottom:16px; display:flex;
                    align-items:center; gap:24px;">
            <div>
                <div style="font-size:2rem; font-weight:800; color:{grade_color};">{grade}</div>
                <div style="color:{grade_color}; opacity:0.85;">Fundamental Score: {score}/100</div>
            </div>
            <div style="flex:1;">
                <div style="background:rgba(255,255,255,0.08); border-radius:8px; height:10px; overflow:hidden;">
                    <div style="width:{score}%; background:{grade_color}; height:100%; border-radius:8px;"></div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Score breakdown ────────────────────────────────────────────────────────
    st.markdown("#### Score Breakdown")
    bd_cols = st.columns(len(breakdown))
    for col, (name, v) in zip(bd_cols, breakdown.items()):
        col.metric(name, f"{v['points']}/{v['max']}", help=v["label"])

    st.divider()

    def _fmt(val, suffix="", prefix=""):
        return f"{prefix}{val:.2f}{suffix}" if val is not None else None

    def _pct(val):
        return f"{val*100:.1f}%" if val is not None else None

    def _show_metrics(items, max_cols=5):
        """Render only metrics whose value is not None, up to max_cols per row."""
        available = [(label, val, kw) for label, val, kw in items if val is not None]
        if not available:
            st.caption("No data available.")
            return
        for i in range(0, len(available), max_cols):
            chunk = available[i:i + max_cols]
            cols = st.columns(len(chunk))
            for col, (label, val, kw) in zip(cols, chunk):
                col.metric(label, val, **kw)

    # ── Valuation ─────────────────────────────────────────────────────────────
    st.markdown("#### Valuation")
    _show_metrics([
        ("Trailing PE",  _fmt(data["pe_trailing"], "x"),  {}),
        ("Forward PE",   _fmt(data["pe_forward"],  "x"),  {}),
        ("Price / Book", _fmt(data["pb_ratio"],    "x"),  {}),
        ("PEG Ratio",    _fmt(data["peg_ratio"],   "x"),  {}),
        ("EV / EBITDA",  _fmt(data["ev_ebitda"],   "x"),  {}),
    ])

    # ── Profitability ─────────────────────────────────────────────────────────
    st.markdown("#### Profitability")
    _show_metrics([
        ("ROE",          _pct(data["roe"]),            {}),
        ("ROA",          _pct(data["roa"]),            {}),
        ("Net Margin",   _pct(data["profit_margin"]),  {}),
        ("Gross Margin", _pct(data["gross_margin"]),   {}),
        ("Op Margin",    _pct(data["op_margin"]),      {}),
    ])

    # ── Growth & Health ───────────────────────────────────────────────────────
    st.markdown("#### Growth & Financial Health")
    _show_metrics([
        ("Revenue Growth",  _pct(data["revenue_growth"]),  {}),
        ("Earnings Growth", _pct(data["earnings_growth"]), {}),
        ("Debt / Equity",   _fmt(data["debt_to_equity"]),  {}),
        ("Current Ratio",   _fmt(data["current_ratio"]),   {}),
        ("Quick Ratio",     _fmt(data["quick_ratio"]),     {}),
        ("Dividend Yield",  _pct(data["dividend_yield"]),  {}),
        ("Payout Ratio",    _pct(data["payout_ratio"]),    {}),
    ])

    st.divider()

    # ── Analyst view ──────────────────────────────────────────────────────────
    st.markdown("#### Analyst View")
    target = data.get("target_price")
    upside_delta = None
    if target and last_price:
        upside = (target - last_price) / last_price * 100
        upside_delta = f"{upside:+.1f}%"
    rec = (data.get("recommendation") or "").replace("_", " ").title() or None
    _show_metrics([
        ("Recommendation", rec,                                                          {}),
        ("Target Price",   f"₹{target:.2f}" if target else None,                        {"delta": upside_delta}),
        ("Analyst Count",  str(data["analyst_count"]) if data.get("analyst_count") else None, {}),
    ])

    st.divider()

    # ── Company info ──────────────────────────────────────────────────────────
    mcap = data.get("market_cap")
    _show_metrics([
        ("Market Cap", f"₹{mcap/1e7:,.0f} Cr" if mcap else None,  {}),
        ("Beta",       _fmt(data.get("beta")),                      {}),
        ("Sector",     data.get("sector") or None,                  {}),
        ("Industry",   data.get("industry") or None,                {}),
    ])


# ── ML prediction render ───────────────────────────────────────────────────────
def render_ml_prediction(df: pd.DataFrame, ticker: str, preloaded_result=None) -> None:
    import plotly.graph_objects as go

    if preloaded_result is not None:
        result = preloaded_result
    else:
        with st.spinner("Training ML model…"):
            result = load_prediction(ticker, "2y")

    if result.get("error"):
        st.warning(f"ML model unavailable: {result['error']}")
        return

    direction = result["direction"]
    probability = result["probability"]
    accuracy = result["accuracy"]
    importance = result["feature_importance"]

    dir_color = "#00C851" if direction == "UP" else "#ff4444"
    dir_icon = "▲" if direction == "UP" else "▼"

    st.markdown(
        f"""
        <div style="background:{dir_color}18; border:2px solid {dir_color};
                    border-radius:12px; padding:16px 24px; margin-bottom:16px;">
            <div style="font-size:2rem; font-weight:800; color:{dir_color};">
                {dir_icon} {direction}
            </div>
            <div style="color:{dir_color}; opacity:0.85; margin-bottom:10px;">
                Predicted next-day direction · Model confidence: {probability*100:.1f}%
            </div>
            <div style="background:rgba(255,255,255,0.08); border-radius:8px; height:10px; overflow:hidden;">
                <div style="width:{probability*100:.1f}%; background:{dir_color}; height:100%; border-radius:8px;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    m1, m2, m3 = st.columns(3)
    m1.metric("Prediction", direction)
    m2.metric("Confidence", f"{probability*100:.1f}%")
    m3.metric("Backtest Accuracy", f"{accuracy*100:.1f}%",
              help=f"Test-set accuracy on {result['test_samples']} held-out days")

    st.divider()

    # ── Feature importance chart ───────────────────────────────────────────────
    st.markdown("#### What drove this prediction")
    sorted_imp = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:8]
    labels = [k.replace("_", " ").title() for k, _ in sorted_imp]
    values = [v for _, v in sorted_imp]

    fig = go.Figure(go.Bar(
        x=values, y=labels,
        orientation="h",
        marker_color="#00d4a0",
        text=[f"{v*100:.1f}%" for v in values],
        textposition="outside",
    ))
    fig.update_layout(
        template="plotly_dark", height=320,
        xaxis_title="Importance", yaxis=dict(autorange="reversed"),
        margin=dict(l=10, r=60, t=20, b=30),
    )
    st.plotly_chart(fig, width="stretch")

    st.caption(
        f"Model: Random Forest (100 trees) · Trained on {result['train_samples']} days · "
        f"Tested on {result['test_samples']} days · "
        "⚠️ ML predictions are probabilistic. Not financial advice."
    )


# ── Main app ───────────────────────────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="NSE Trading Dashboard",
        page_icon="assets/favicon.svg",
        layout="wide",
    )
    inject_css()

    # ── Top navbar ─────────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    /* Navbar pill styling */
    div[data-testid="stRadio"]:has(input[value="📈 Equities"]) div[role="radiogroup"] {
        gap: 6px;
    }
    div[data-testid="stRadio"]:has(input[value="📈 Equities"]) div[role="radiogroup"] label {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 10px;
        padding: 9px 28px;
        cursor: pointer;
        font-weight: 600;
        font-size: 0.97rem;
        transition: all 0.15s;
        color: rgba(255,255,255,0.55);
    }
    div[data-testid="stRadio"]:has(input[value="📈 Equities"]) div[role="radiogroup"] label:hover {
        background: rgba(0,212,160,0.07);
        border-color: rgba(0,212,160,0.35);
        color: rgba(0,212,160,0.85);
    }
    div[data-testid="stRadio"]:has(input[value="📈 Equities"]) div[role="radiogroup"] label:has(input:checked) {
        background: rgba(0,212,160,0.13) !important;
        border-color: rgba(0,212,160,0.55) !important;
        color: #00d4a0 !important;
    }
    div[data-testid="stRadio"]:has(input[value="📈 Equities"]) div[role="radiogroup"] label > div:first-child {
        display: none;
    }
    </style>
    """, unsafe_allow_html=True)

    section = st.radio(
        "nav",
        ["📈 Equities", "🎯 Index Options"],
        horizontal=True,
        label_visibility="collapsed",
        key="top_nav",
    )

    if section == "🎯 Index Options":
        st.switch_page("pages/index_options.py")
    st.divider()

    _header_placeholder = st.empty()

    # ── Sidebar ────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("Settings")
        st.divider()

        if section == "📈 Equities":
            @st.cache_data(ttl=86400, show_spinner=False)
            def _build_unified_options() -> list[tuple[str, str]]:
                """Fetch full NSE equity list from NSE archives.
                Returns list of (display_label, nse_symbol) where display_label =
                'Company Full Name (TICKER)' — searchable by either.
                Filters out test/numeric symbols. Default sorted by company name.
                """
                import io
                import requests as _req
                try:
                    resp = _req.get(
                        "https://archives.nseindia.com/content/equities/EQUITY_L.csv",
                        timeout=15,
                        headers={"User-Agent": "Mozilla/5.0"},
                    )
                    resp.raise_for_status()
                    import pandas as _pd
                    df = _pd.read_csv(io.StringIO(resp.text))
                    sym_col  = "SYMBOL"
                    name_col = "NAME OF COMPANY"
                    df = df[[sym_col, name_col]].dropna()
                    df.columns = ["sym", "name"]
                    # Filter out test entries and purely numeric symbols
                    df = df[~df["sym"].str.contains("NSETEST", na=False)]
                    df = df[~df["sym"].str.match(r"^\d", na=False)]
                    df["name"] = df["name"].str.strip().str.title()
                    df["sym"]  = df["sym"].str.strip().str.upper()
                    df = df.sort_values("name")
                    return [(f"{row.name} ({row.sym})", row.sym) for row in df.itertuples(index=False)]
                except Exception:
                    # Fallback to hardcoded list
                    all_stocks = {**NIFTY50, **OTHER_STOCKS}
                    entries = sorted(
                        [(f"{name} ({v.replace('.NS','').replace('.BO','')})",
                          v.replace(".NS","").replace(".BO",""))
                         for name, v in all_stocks.items()],
                        key=lambda x: x[0]
                    )
                    return entries

            unified_options = _build_unified_options()
            labels  = [label for label, _ in unified_options]
            sym_map = {label: sym for label, sym in unified_options}
            # name lookup: "RELIANCE" → "Reliance Industries Limited"
            sym_to_name = {sym: label.rsplit(" (", 1)[0] for label, sym in unified_options}

            # Default to Reliance Industries
            default_idx = next(
                (i + 1 for i, (_, s) in enumerate(unified_options) if s == "RELIANCE"),
                1,
            )
            sel_label = st.selectbox(
                "Search stock (name or ticker)",
                options=[""] + labels,
                index=default_idx,
                format_func=lambda x: "— type name or ticker —" if x == "" else x,
            )

            if sel_label:
                raw_sym = sym_map[sel_label]
                ticker  = raw_sym + ".NS"
                selected_display = sym_to_name.get(raw_sym, raw_sym)
            else:
                ticker = "RELIANCE.NS"
                selected_display = "Reliance Industries Limited"
            interval = st.selectbox("Interval", ["5m", "15m", "30m", "1h", "1d", "1wk"], index=4)
            valid_periods = VALID_COMBOS[interval]
            period = st.selectbox("Period", valid_periods, index=min(2, len(valid_periods) - 1))
        else:
            opt_index = st.selectbox(
                "Select Index",
                ["NIFTY", "BANKNIFTY", "MIDCPNIFTY"],
                format_func=lambda x: {"NIFTY": "Nifty 50", "BANKNIFTY": "Bank Nifty", "MIDCPNIFTY": "Midcap Nifty"}[x],
            )

        refresh = st.button("🔄 Refresh")
        if refresh:
            st.cache_data.clear()

        st.divider()
        st.caption("📡 Equity data: Angel One → Yahoo Finance fallback")
        st.caption("Options data: NSE live chain")
        st.caption("⚠️ For educational purposes only. Not financial advice.")

    # ══════════════════════════════════════════════════════════════════════════
    # ══════════════════════════════════════════════════════════════════════════
    # SECTION: Equities
    # ══════════════════════════════════════════════════════════════════════════
    if section == "📈 Equities":
        # Fill header now that we know the selected stock
        with _header_placeholder:
            page_header(selected_display, "Real-time technical analysis · BUY / SELL / HOLD signals")

        with st.spinner(f"Fetching {ticker} ({interval}, {period})…"):
            try:
                df = load_data(ticker, interval, period)
                sig = generate_signal(df)
            except Exception as e:
                st.error(f"Error loading data: {e}")
                st.stop()

        support = df.attrs.get("support")
        resistance = df.attrs.get("resistance")

        # ── Pre-load fundamentals + ML ─────────────────────────────────────────
        with st.spinner("Analysing…"):
            fund_data   = load_fundamentals(ticker)
            fund_result = score_fundamentals(fund_data, current_price=sig["last_price"])
            ml_result   = load_prediction(ticker, "2y")

        # ── Derive per-source signals ──────────────────────────────────────────
        # Technical
        tech_signal = sig["signal"]
        tech_conf   = sig["confidence"]

        # Fundamentals → BUY / HOLD / SELL
        if fund_result["score"] >= 60:
            fund_signal, fund_conf = "BUY",  fund_result["score"]
        elif fund_result["score"] < 40:
            fund_signal, fund_conf = "SELL", 100 - fund_result["score"]
        else:
            fund_signal, fund_conf = "HOLD", fund_result["score"]

        # ML
        if ml_result.get("error"):
            ml_signal, ml_conf = "HOLD", 50
        else:
            ml_signal = "BUY" if ml_result["direction"] == "UP" else "SELL"
            ml_conf   = int(ml_result["probability"] * 100)

        def _signal_card(col, icon, label, signal, conf, subtitle):
            color = "#00C851" if signal == "BUY" else ("#ff4444" if signal == "SELL" else "#ffbb33")
            col.markdown(
                f"""
                <div style="background:{color}14; border:2px solid {color}88;
                            border-radius:12px; padding:14px 18px;
                            min-height:120px; box-sizing:border-box;">
                  <div style="font-size:0.75em; color:#aaa; margin-bottom:2px;">{icon} {label}</div>
                  <div style="font-size:1.9em; font-weight:800; color:{color}; line-height:1.1;">{signal}</div>
                  <div style="font-size:0.82em; color:{color}; opacity:0.85; margin-top:2px;">{subtitle}</div>
                  <div style="background:rgba(255,255,255,0.08); border-radius:6px; height:6px;
                              overflow:hidden; margin-top:8px;">
                    <div style="width:{conf}%; background:{color}; height:100%; border-radius:6px;"></div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ── Three signal cards + price info ───────────────────────────────────
        card_tech, card_fund, card_ml, col_price, col_sl, col_tgt = st.columns([1.4, 1.4, 1.4, 1, 1, 1])
        _signal_card(card_tech, "📊", "Technical",     tech_signal, tech_conf,
                     f"Confidence: {tech_conf}%")
        _signal_card(card_fund, "📋", "Fundamentals",  fund_signal, fund_conf,
                     f"{fund_result['grade']} · Score {fund_result['score']}/100")
        _signal_card(card_ml,   "🤖", "ML Prediction", ml_signal,  ml_conf,
                     f"Model confidence: {ml_conf}%" if not ml_result.get("error") else "Unavailable")
        col_price.metric("Last Price", f"₹{sig['last_price']:,.2f}")
        col_sl.metric("Stop Loss",     f"₹{sig['stop_loss']:,.2f}")
        col_tgt.metric("Target",       f"₹{sig['target']:,.2f}")

        st.divider()

        tab_tech, tab_fund, tab_ml = st.tabs(["📊 Technical", "📋 Fundamentals", "🤖 ML Prediction"])

        _zoom_cfg = {"scrollZoom": True, "displayModeBar": True, "plotGlPixelRatio": 1}
        with tab_tech:
            st.plotly_chart(build_price_chart(df, support, resistance), width='stretch', config=_zoom_cfg, key="chart_price")
            col_rsi, col_macd = st.columns(2)
            with col_rsi:
                st.plotly_chart(build_rsi_chart(df), width='stretch', config=_zoom_cfg, key="chart_rsi")
            with col_macd:
                st.plotly_chart(build_macd_chart(df), width='stretch', config=_zoom_cfg, key="chart_macd")
            st.plotly_chart(build_volume_obv_chart(df), width='stretch', config=_zoom_cfg, key="chart_volume")
            st.subheader("Indicator Breakdown")
            render_indicator_table(sig["components"])
            with st.expander("View raw data"):
                st.dataframe(df.tail(50), width="stretch")

        with tab_fund:
            render_fundamentals(ticker, sig["last_price"], preloaded_data=fund_data, preloaded_result=fund_result)

        with tab_ml:
            render_ml_prediction(df, ticker, preloaded_result=ml_result)

    else:
        with _header_placeholder:
            page_header("NSE / BSE Trading Dashboard", "Real-time technical analysis · BUY / SELL / HOLD signals")

    # Index Options section now lives in index_options.py (reached via st.switch_page above)


if __name__ == "__main__":
    main()
