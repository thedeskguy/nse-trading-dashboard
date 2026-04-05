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

# ── Nifty 50 tickers ──────────────────────────────────────────────────────────
NIFTY50 = {
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

SIGNAL_COLORS = {"BUY": "#00C851", "SELL": "#ff4444", "HOLD": "#ffbb33"}


# ── Data fetching (cached 5 min) ───────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data(ticker: str, interval: str, period: str):
    df = fetch_ohlcv(ticker, interval=interval, period=period)
    df = compute_all(df)
    return df


# ── Chart builders ─────────────────────────────────────────────────────────────
def build_price_chart(df: pd.DataFrame, support, resistance) -> go.Figure:
    fig = go.Figure()

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        name="Price", increasing_line_color="#26a69a", decreasing_line_color="#ef5350",
    ))

    # Bollinger Bands (shaded)
    if "BB_upper" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_upper"], name="BB Upper",
            line=dict(color="rgba(150,150,255,0.5)", width=1), showlegend=True,
        ))
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_lower"], name="BB Lower",
            line=dict(color="rgba(150,150,255,0.5)", width=1),
            fill="tonexty", fillcolor="rgba(150,150,255,0.07)", showlegend=True,
        ))

    # EMAs
    ema_colors = {"EMA_9": "#FFD700", "EMA_21": "#FF8C00", "EMA_50": "#00BFFF", "EMA_200": "#FF69B4"}
    for col, color in ema_colors.items():
        if col in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col], name=col.replace("_", " "),
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
    )
    return fig


def build_rsi_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    col = "RSI_14"
    if col not in df.columns:
        return fig

    rsi = df[col]
    colors = ["#00C851" if v < 30 else "#ff4444" if v > 70 else "#888" for v in rsi]

    fig.add_trace(go.Scatter(
        x=df.index, y=rsi, name="RSI(14)",
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
        yaxis=dict(range=[0, 100]),
        margin=dict(l=0, r=0, t=40, b=0), showlegend=False,
    )
    return fig


def build_macd_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if "MACD" not in df.columns:
        return fig

    hist = df["MACD_hist"]
    bar_colors = ["#00C851" if v >= 0 else "#ef5350" for v in hist.fillna(0)]

    fig.add_trace(go.Bar(
        x=df.index, y=hist, name="Histogram",
        marker_color=bar_colors, opacity=0.7,
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df["MACD"], name="MACD",
        line=dict(color="#2196F3", width=1.5),
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df["MACD_signal"], name="Signal",
        line=dict(color="#FF9800", width=1.5),
    ))
    fig.add_hline(y=0, line_color="rgba(150,150,150,0.4)", line_width=1)

    fig.update_layout(
        title="MACD (12, 26, 9)", height=220, template="plotly_dark",
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(orientation="h", y=1.05),
    )
    return fig


def build_volume_obv_chart(df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    vol_colors = [
        "#26a69a" if df["Close"].iloc[i] >= df["Open"].iloc[i] else "#ef5350"
        for i in range(len(df))
    ]
    fig.add_trace(go.Bar(
        x=df.index, y=df["Volume"], name="Volume",
        marker_color=vol_colors, opacity=0.7,
    ), secondary_y=False)

    if "OBV" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["OBV"], name="OBV",
            line=dict(color="#E040FB", width=1.5),
        ), secondary_y=True)

    fig.update_layout(
        title="Volume + OBV", height=220, template="plotly_dark",
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(orientation="h", y=1.05),
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


# ── Main app ───────────────────────────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="NSE Trading Dashboard",
        page_icon="assets/favicon.svg",
        layout="wide",
    )
    inject_css()
    page_header("NSE / BSE Trading Dashboard", "Real-time technical analysis · BUY / SELL / HOLD signals")

    # ── Sidebar ────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("Settings")

        tab_choice = st.radio("View", ["📊 Stocks / Charts", "🎯 Index Options"], label_visibility="collapsed")

        st.divider()

        if tab_choice == "📊 Stocks / Charts":
            selected_name = st.selectbox("Select Stock (Nifty 50)", list(NIFTY50.keys()))
            custom_ticker = st.text_input(
                "Or enter custom ticker",
                placeholder="e.g. TATAMOTORS.NS",
                help="Append .NS for NSE, .BO for BSE",
            )
            ticker = custom_ticker.strip().upper() if custom_ticker.strip() else NIFTY50[selected_name]
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
        st.caption("Options data: NSE live chain")
        st.caption("Equity data: Yahoo Finance (15-min delay intraday)")
        st.caption("⚠️ For educational purposes only. Not financial advice.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1: Stocks / Charts
    # ══════════════════════════════════════════════════════════════════════════
    if tab_choice == "📊 Stocks / Charts":
        with st.spinner(f"Fetching {ticker} ({interval}, {period})…"):
            try:
                df = load_data(ticker, interval, period)
                sig = generate_signal(df)
            except Exception as e:
                st.error(f"Error loading data: {e}")
                st.stop()

        support = df.attrs.get("support")
        resistance = df.attrs.get("resistance")

        col1, col2, col3, col4, col5 = st.columns([1.4, 1, 1, 1, 1])
        with col1:
            render_signal_badge(sig["signal"], sig["confidence"])
        with col2:
            st.metric("Last Price", f"₹{sig['last_price']:,.2f}")
        with col3:
            st.metric("Confidence", f"{sig['confidence']}%")
        with col4:
            label = "Stop Loss" if sig["signal"] != "HOLD" else "SL (est.)"
            st.metric(label, f"₹{sig['stop_loss']:,.2f}")
        with col5:
            label = "Target" if sig["signal"] != "HOLD" else "Target (est.)"
            st.metric(label, f"₹{sig['target']:,.2f}")

        st.divider()
        st.plotly_chart(build_price_chart(df, support, resistance), width="stretch")
        col_rsi, col_macd = st.columns(2)
        with col_rsi:
            st.plotly_chart(build_rsi_chart(df), width="stretch")
        with col_macd:
            st.plotly_chart(build_macd_chart(df), width="stretch")
        st.plotly_chart(build_volume_obv_chart(df), width="stretch")

        st.subheader("Indicator Breakdown")
        render_indicator_table(sig["components"])

        with st.expander("View raw data"):
            st.dataframe(df.tail(50), width="stretch")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2: Index Options
    # ══════════════════════════════════════════════════════════════════════════
    else:
        index_names = {"NIFTY": "Nifty 50", "BANKNIFTY": "Bank Nifty", "MIDCPNIFTY": "Midcap Nifty"}
        st.subheader(f"🎯 Options Recommendation — {index_names[opt_index]}")

        with st.spinner(f"Fetching {opt_index} options chain from NSE…"):
            try:
                opt_result = load_options(opt_index)
            except ConnectionError as e:
                st.error(f"NSE connection failed: {e}")
                st.info("NSE occasionally blocks automated requests. Wait 10–15 seconds and click Refresh.")
                st.stop()
            except Exception as e:
                st.error(f"Error: {e}")
                st.stop()

        # ── Header metrics ─────────────────────────────────────────────────
        h1, h2, h3, h4, h5 = st.columns(5)
        h1.metric(f"{opt_index} Spot", f"₹{opt_result['spot']:,.2f}")
        h2.metric("Trend Signal", opt_result["underlying_signal"])
        h3.metric("Confidence", f"{opt_result['confidence']}%")
        pcr = opt_result["pcr"]
        h4.metric("Put/Call Ratio", str(pcr.get("pcr", "N/A")), help=pcr.get("signal", ""))
        if opt_result.get("max_pain"):
            h5.metric("Max Pain", f"₹{opt_result['max_pain']:,.0f}", help="Strike where option buyers lose most near expiry")

        st.markdown(f"**{opt_result['message']}** &nbsp;|&nbsp; *Data as of {opt_result.get('timestamp', 'N/A')}*")
        st.divider()

        if opt_result["underlying_signal"] == "HOLD":
            st.warning("⏸️ No options trade recommended — trend signals are mixed. Wait for a clearer directional move.")
        else:
            recs = opt_result.get("recommendations", {})

            col_intra, col_pos = st.columns(2)
            with col_intra:
                st.markdown("#### Intraday Trade")
                render_option_card("Intraday", recs.get("intraday"), "#00C851" if opt_result["option_type"] == "CALL" else "#FF6B6B")
                with st.expander("ℹ️ Intraday Rules"):
                    st.markdown("""
- **Entry**: At market open or on first 15-min candle confirmation
- **Exit**: Compulsory before 3:15 PM — do NOT carry intraday options overnight
- **Stop Loss**: Exit immediately if premium falls to the SL level shown above
- **Strike**: ATM (At The Money) for maximum delta and quick response to index move
""")

            with col_pos:
                st.markdown("#### Positional Trade (2–5 days)")
                render_option_card("Positional", recs.get("positional"), "#00C851" if opt_result["option_type"] == "CALL" else "#FF6B6B")
                with st.expander("ℹ️ Positional Rules"):
                    st.markdown("""
- **Entry**: End of day or on next morning's open
- **Expiry**: Next weekly expiry (avoids aggressive theta on near expiry)
- **Exit**: At target, at stop loss, or 1 day before expiry (whichever comes first)
- **Risk**: Overnight gap risk — size positions accordingly (1 lot max to start)
""")

        # ── PCR + Max Pain context ─────────────────────────────────────────
        st.divider()
        st.markdown("#### Market Sentiment")
        s1, s2 = st.columns(2)
        with s1:
            pcr_val = pcr.get("pcr")
            if pcr_val:
                pcr_color = "#00C851" if pcr_val > 1.2 else ("#ff4444" if pcr_val < 0.8 else "#ffbb33")
                st.markdown(f"""
<div style="border:1px solid {pcr_color}; border-radius:8px; padding:12px;">
<b>Put/Call Ratio (OI): {pcr_val}</b><br>
{pcr.get('signal', '')}
<br><small>PCR > 1.2 = Bullish &nbsp;|&nbsp; PCR < 0.8 = Bearish &nbsp;|&nbsp; 0.8–1.2 = Neutral</small>
</div>""", unsafe_allow_html=True)
        with s2:
            if opt_result.get("max_pain"):
                st.markdown(f"""
<div style="border:1px solid #888; border-radius:8px; padding:12px;">
<b>Max Pain: ₹{opt_result['max_pain']:,.0f}</b><br>
Market makers profit most if index closes here on expiry day.
<br><small>Spot vs Max Pain: {'+' if opt_result['spot'] > opt_result['max_pain'] else ''}{opt_result['spot'] - opt_result['max_pain']:,.0f} pts</small>
</div>""", unsafe_allow_html=True)

        # ── Options chain table ────────────────────────────────────────────
        st.divider()
        st.markdown("#### Live Options Chain (ATM ± 10 strikes)")
        try:
            from tools.fetch_options_chain import fetch_options_chain
            chain_data = fetch_options_chain(opt_index)
            expiry_dates = chain_data["expiry_dates"]
            selected_expiry = st.selectbox("Expiry", expiry_dates[:6]) if expiry_dates else None
            if selected_expiry:
                render_options_chain_table(chain_data["chain"], opt_result["spot"], selected_expiry, opt_index)
        except Exception as e:
            st.warning(f"Could not load options chain table: {e}")

        # ── Indicator breakdown (underlying) ───────────────────────────────
        with st.expander("View underlying indicator breakdown"):
            render_indicator_table(opt_result["signal_components"])


if __name__ == "__main__":
    main()
