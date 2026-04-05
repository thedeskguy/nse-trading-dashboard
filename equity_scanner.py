"""
Equity Buy Scanner — Top 100 Indian Companies (Market Cap > ₹4,000 Cr)
Scans Nifty 100 stocks for BUY setups and shows entry, stop-loss, and target.
Only buy-side recommendations. No shorts, no futures.
Universe: Nifty 50 + Nifty Next 50 (all constituents have market cap well above ₹4,000 Cr)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from concurrent.futures import ThreadPoolExecutor, as_completed
from streamlit_autorefresh import st_autorefresh

from tools.fetch_stock_data import fetch_ohlcv
from tools.compute_indicators import compute_all
from tools.generate_signals import generate_signal
from tools.theme import inject_css, signal_badge, page_header, SIGNAL_COLORS

# ── Stock universe ─────────────────────────────────────────────────────────────

# Nifty 100 = Nifty 50 + Nifty Next 50
# All constituents have market cap >> ₹4,000 Crore
TOP100 = {
    # ── Nifty 50 ──────────────────────────────────────────────────────────────
    "Reliance Industries":    "RELIANCE.NS",
    "TCS":                    "TCS.NS",
    "HDFC Bank":              "HDFCBANK.NS",
    "ICICI Bank":             "ICICIBANK.NS",
    "Infosys":                "INFY.NS",
    "Kotak Mahindra Bank":    "KOTAKBANK.NS",
    "L&T":                    "LT.NS",
    "SBI":                    "SBIN.NS",
    "Axis Bank":              "AXISBANK.NS",
    "Bharti Airtel":          "BHARTIARTL.NS",
    "Asian Paints":           "ASIANPAINT.NS",
    "Bajaj Finance":          "BAJFINANCE.NS",
    "HCL Technologies":       "HCLTECH.NS",
    "Wipro":                  "WIPRO.NS",
    "Maruti Suzuki":          "MARUTI.NS",
    "Titan":                  "TITAN.NS",
    "Sun Pharma":             "SUNPHARMA.NS",
    "NTPC":                   "NTPC.NS",
    "Tata Motors":            "TATAMOTORS.NS",
    "Tata Steel":             "TATASTEEL.NS",
    "Hindalco":               "HINDALCO.NS",
    "Tech Mahindra":          "TECHM.NS",
    "Coal India":             "COALINDIA.NS",
    "ONGC":                   "ONGC.NS",
    "Dr Reddy's":             "DRREDDY.NS",
    "Cipla":                  "CIPLA.NS",
    "Eicher Motors":          "EICHERMOT.NS",
    "Bajaj Auto":             "BAJAJ-AUTO.NS",
    "Hero MotoCorp":          "HEROMOTOCO.NS",
    "Mahindra & Mahindra":    "M&M.NS",
    "IndusInd Bank":          "INDUSINDBK.NS",
    "Britannia":              "BRITANNIA.NS",
    "Tata Consumer":          "TATACONSUM.NS",
    "BPCL":                   "BPCL.NS",
    "Apollo Hospitals":       "APOLLOHOSP.NS",
    "LTIMindtree":            "LTIM.NS",
    "Power Grid":             "POWERGRID.NS",
    "UltraTech Cement":       "ULTRACEMCO.NS",
    "Nestle India":           "NESTLEIND.NS",
    "Grasim":                 "GRASIM.NS",
    "Adani Enterprises":      "ADANIENT.NS",
    "Adani Ports":            "ADANIPORTS.NS",
    "JSW Steel":              "JSWSTEEL.NS",
    "ITC":                    "ITC.NS",
    "SBI Life Insurance":     "SBILIFE.NS",
    "HDFC Life Insurance":    "HDFCLIFE.NS",
    "Bajaj Finserv":          "BAJAJFINSV.NS",
    "Divi's Laboratories":    "DIVISLAB.NS",
    "Shriram Finance":        "SHRIRAMFIN.NS",
    "Trent":                  "TRENT.NS",
    # ── Nifty Next 50 ─────────────────────────────────────────────────────────
    "Ambuja Cements":         "AMBUJACEM.NS",
    "Bank of Baroda":         "BANKBARODA.NS",
    "Berger Paints":          "BERGEPAINT.NS",
    "Bosch":                  "BOSCHLTD.NS",
    "Canara Bank":            "CANBK.NS",
    "Cholamandalam Finance":  "CHOLAFIN.NS",
    "Colgate":                "COLPAL.NS",
    "DLF":                    "DLF.NS",
    "Godrej Consumer":        "GODREJCP.NS",
    "Havells":                "HAVELLS.NS",
    "ICICI Prudential Life":  "ICICIPRULI.NS",
    "ICICI Lombard":          "ICICIGI.NS",
    "Indus Towers":           "INDUSTOWER.NS",
    "Jindal Steel":           "JINDALSTEL.NS",
    "Lupin":                  "LUPIN.NS",
    "Muthoot Finance":        "MUTHOOTFIN.NS",
    "Info Edge (Naukri)":     "NAUKRI.NS",
    "Pidilite":               "PIDILITIND.NS",
    "Punjab National Bank":   "PNB.NS",
    "REC Limited":            "RECLTD.NS",
    "SAIL":                   "SAIL.NS",
    "Siemens":                "SIEMENS.NS",
    "SRF":                    "SRF.NS",
    "Torrent Pharma":         "TORNTPHARM.NS",
    "TVS Motor":              "TVSMOTOR.NS",
    "Vedanta":                "VEDL.NS",
    "Voltas":                 "VOLTAS.NS",
    "Zydus Lifesciences":     "ZYDUSLIFE.NS",
    "Marico":                 "MARICO.NS",
    "PI Industries":          "PIIND.NS",
    "Aurobindo Pharma":       "AUROPHARMA.NS",
    "Samvardhana Motherson":  "MOTHERSON.NS",
    "Balkrishna Industries":  "BALKRISIND.NS",
    "Max Healthcare":         "MAXHEALTH.NS",
    "Indian Oil Corp":        "IOC.NS",
    "Hindustan Petroleum":    "HPCL.NS",
    "Dabur":                  "DABUR.NS",
    "Mphasis":                "MPHASIS.NS",
    "Persistent Systems":     "PERSISTENT.NS",
    "Coforge":                "COFORGE.NS",
    "L&T Tech Services":      "LTTS.NS",
    "KPIT Technologies":      "KPITTECH.NS",
    "Zomato":                 "ZOMATO.NS",
    "IRCTC":                  "IRCTC.NS",
    "HAL":                    "HAL.NS",
    "Bharat Electronics":     "BEL.NS",
    "CDSL":                   "CDSL.NS",
    "Adani Green Energy":     "ADANIGREEN.NS",
    "GMR Airports":           "GMRINFRA.NS",
    "Page Industries":        "PAGEIND.NS",
    "Torrent Power":          "TORNTPOWER.NS",
}

# Keep the old name for backward compatibility within the file
NIFTY50 = TOP100

MARKET_INDICES = {
    "Nifty 50":    "^NSEI",
    "Bank Nifty":  "^NSEBANK",
    "Sensex":      "^BSESN",
}


# ── Caching ────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def get_signal_for(ticker: str, interval: str, period: str) -> dict | None:
    """Fetch data + compute indicators + generate signal for one ticker."""
    try:
        df = fetch_ohlcv(ticker, interval=interval, period=period)
        df = compute_all(df)
        sig = generate_signal(df)
        sig["df"] = df          # attach for chart rendering
        sig["ticker"] = ticker
        return sig
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


@st.cache_data(ttl=300, show_spinner=False)
def get_market_mood(interval: str, period: str) -> dict:
    """Get Nifty 50 trend signal."""
    try:
        df = fetch_ohlcv("^NSEI", interval=interval, period=period)
        df = compute_all(df)
        sig = generate_signal(df)
        return sig
    except Exception as e:
        return {"error": str(e), "signal": "UNKNOWN", "confidence": 0}


@st.cache_data(ttl=300, show_spinner=False)
def scan_all_stocks(interval: str, period: str) -> list[dict]:
    """Parallel scan of all Nifty 50 stocks."""
    results = []
    name_map = {v: k for k, v in NIFTY50.items()}

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(get_signal_for, ticker, interval, period): ticker
            for ticker in NIFTY50.values()
        }
        for future in as_completed(futures):
            ticker = futures[future]
            result = future.result()
            if result and "error" not in result:
                result["name"] = name_map.get(ticker, ticker)
                results.append(result)

    return results


# ── Chart helpers ──────────────────────────────────────────────────────────────

def build_stock_chart(df: pd.DataFrame, sig: dict, stock_name: str) -> go.Figure:
    """Full candlestick + indicator chart for a selected stock."""
    support = df.attrs.get("support")
    resistance = df.attrs.get("resistance")

    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        row_heights=[0.5, 0.17, 0.17, 0.16],
        vertical_spacing=0.03,
        subplot_titles=("Price + EMAs + Bollinger", "RSI (14)", "MACD", "Volume + OBV"),
    )

    # ── Row 1: Candlestick ────────────────────────────────────────────────────
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        name="Price", increasing_line_color="#26a69a", decreasing_line_color="#ef5350",
        showlegend=False,
    ), row=1, col=1)

    # Bollinger bands (filled area)
    if "BB_upper" in df.columns and "BB_lower" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_upper"], line=dict(color="rgba(100,149,237,0.4)", width=1),
            name="BB Upper", showlegend=False,
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_lower"], line=dict(color="rgba(100,149,237,0.4)", width=1),
            fill="tonexty", fillcolor="rgba(100,149,237,0.05)",
            name="BB Lower", showlegend=False,
        ), row=1, col=1)

    # EMAs
    ema_styles = {
        "EMA_9":   ("#FFD700", 1, "EMA 9"),
        "EMA_21":  ("#FF8C00", 1, "EMA 21"),
        "EMA_50":  ("#00BFFF", 1.5, "EMA 50"),
        "EMA_200": ("#FF4500", 2, "EMA 200"),
    }
    for col, (color, width, label) in ema_styles.items():
        if col in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col], line=dict(color=color, width=width),
                name=label, showlegend=True,
            ), row=1, col=1)

    # Support / Resistance
    price = sig["last_price"]
    if support:
        fig.add_hline(y=support, line_dash="dash", line_color="lime", line_width=1,
                      annotation_text=f"S {support:.0f}", row=1, col=1)
    if resistance:
        fig.add_hline(y=resistance, line_dash="dash", line_color="red", line_width=1,
                      annotation_text=f"R {resistance:.0f}", row=1, col=1)

    # Entry / SL / Target markers
    fig.add_hline(y=price, line_dash="dot", line_color="white", line_width=1,
                  annotation_text=f"Entry {price:.2f}", row=1, col=1)
    fig.add_hline(y=sig["stop_loss"], line_dash="dot", line_color="#ff5252", line_width=1,
                  annotation_text=f"SL {sig['stop_loss']:.2f}", row=1, col=1)
    fig.add_hline(y=sig["target"], line_dash="dot", line_color="#69f0ae", line_width=1,
                  annotation_text=f"Target {sig['target']:.2f}", row=1, col=1)

    # ── Row 2: RSI ────────────────────────────────────────────────────────────
    if "RSI_14" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["RSI_14"], line=dict(color="#ba68c8", width=1.5),
            name="RSI", showlegend=False,
        ), row=2, col=1)
        fig.add_hrect(y0=70, y1=100, fillcolor="rgba(239,83,80,0.15)", line_width=0, row=2, col=1)
        fig.add_hrect(y0=0, y1=30, fillcolor="rgba(38,166,154,0.15)", line_width=0, row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="rgba(239,83,80,0.5)", line_width=1, row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="rgba(38,166,154,0.5)", line_width=1, row=2, col=1)

    # ── Row 3: MACD ───────────────────────────────────────────────────────────
    if "MACD" in df.columns and "MACD_signal" in df.columns:
        colors = ["#26a69a" if v >= 0 else "#ef5350" for v in df["MACD_hist"].fillna(0)]
        fig.add_trace(go.Bar(
            x=df.index, y=df["MACD_hist"], marker_color=colors,
            name="MACD Hist", showlegend=False,
        ), row=3, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["MACD"], line=dict(color="#2196f3", width=1.5),
            name="MACD", showlegend=False,
        ), row=3, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["MACD_signal"], line=dict(color="#ff9800", width=1.5),
            name="Signal", showlegend=False,
        ), row=3, col=1)

    # ── Row 4: Volume ─────────────────────────────────────────────────────────
    vol_colors = ["#26a69a" if c >= o else "#ef5350"
                  for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(
        x=df.index, y=df["Volume"], marker_color=vol_colors,
        name="Volume", showlegend=False, opacity=0.6,
    ), row=4, col=1)

    # OBV on secondary y-axis
    if "OBV" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["OBV"], line=dict(color="#ffeb3b", width=1),
            name="OBV", yaxis="y5", showlegend=False,
        ), row=4, col=1)

    fig.update_layout(
        title=f"{stock_name} — Technical Analysis",
        template="plotly_dark",
        height=900,
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", y=1.02, x=0),
        margin=dict(l=50, r=50, t=60, b=20),
    )
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="RSI", row=2, col=1, range=[0, 100])
    fig.update_yaxes(title_text="MACD", row=3, col=1)
    fig.update_yaxes(title_text="Volume", row=4, col=1)

    return fig


def confidence_bar(confidence: int) -> str:
    """Build a simple text progress bar."""
    filled = int(confidence / 5)
    return "█" * filled + "░" * (20 - filled) + f"  {confidence}%"


# ── Main app ───────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="Equity Buy Scanner",
        page_icon="assets/favicon.svg",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_css()

    # ── Live auto-refresh ─────────────────────────────────────────────────────
    _refresh_options = {"Off": 0, "1 min": 60, "2 min": 120, "5 min": 300, "10 min": 600}
    with st.sidebar:
        st.subheader("⚡ Live Refresh")
        _selected_refresh = st.selectbox("Auto-refresh interval", list(_refresh_options.keys()), index=3, key="eq_refresh_sel")
        _refresh_secs = _refresh_options[_selected_refresh]
        if _refresh_secs > 0:
            _count = st_autorefresh(interval=_refresh_secs * 1000, key="equity_autorefresh")
            if _count > 0:
                st.cache_data.clear()
            st.caption(f"Refresh #{_count} · every {_selected_refresh}")
        else:
            st.caption("Auto-refresh is off.")

    # Sidebar
    with st.sidebar:
        st.title("⚙️ Settings")

        interval = st.selectbox(
            "Timeframe",
            ["1d", "1wk", "1h", "30m"],
            index=0,
            help="Chart interval for analysis",
        )
        period_map = {
            "1d":  ["1y", "6mo", "3mo"],
            "1wk": ["2y", "1y", "6mo"],
            "1h":  ["6mo", "3mo", "1mo"],
            "30m": ["3mo", "1mo", "5d"],
        }
        period = st.selectbox("Lookback", period_map[interval])

        min_confidence = st.slider(
            "Min Confidence for BUY",
            min_value=55, max_value=85, value=62, step=1,
            help="Only show stocks with BUY confidence above this threshold",
        )

        st.divider()

        # ── Search any NSE stock ──────────────────────────────────────────
        st.subheader("🔎 Search Any Stock")
        search_query = st.text_input(
            "Stock name or symbol",
            placeholder="e.g. HDFC, Zomato, Paytm...",
            help="Searches all NSE equities via Angel One",
        )
        if search_query and len(search_query) >= 2:
            try:
                from tools.angel_auth import get_session as _angel_session
                obj = _angel_session()
                hits = obj.searchScrip("NSE", search_query)
                matches = (hits or {}).get("data", []) or []
                # Angel One marks equity stocks with "-EQ" suffix
                equities = [
                    m for m in matches
                    if str(m.get("tradingsymbol", "")).endswith("-EQ")
                ]
                if equities:
                    options = {
                        m["tradingsymbol"].replace("-EQ", ""): m["tradingsymbol"].replace("-EQ", "")
                        for m in equities[:15]
                    }
                    chosen_sym = st.selectbox("Select stock", list(options.keys()))
                    if st.button("Analyse →", use_container_width=True):
                        st.session_state["custom_ticker"] = chosen_sym + ".NS"
                        st.session_state["custom_name"]   = chosen_sym
                elif matches:
                    st.caption("No equity matches (only MF/ETF found). Try the exact NSE symbol, e.g. ZOMATO.")
                else:
                    st.caption("No results. Try exact NSE symbol, e.g. ZOMATO.")
            except Exception as e:
                st.caption(f"Search unavailable: rate limit. Try after a moment.")

        st.divider()
        refresh = st.button("🔄 Refresh Data", use_container_width=True)
        if refresh:
            st.cache_data.clear()
            st.session_state.pop("custom_ticker", None)
            st.session_state.pop("custom_name", None)

        st.caption("Data cached for 5 minutes. Click Refresh to force reload.")

    # ── Header ────────────────────────────────────────────────────────────────
    page_header(
        "Equity Buy Scanner — Nifty 100",
        "Nifty 50 + Nifty Next 50 · BUY signals only · Entry + Stop Loss + Target",
    )

    # ── Market Mood ──────────────────────────────────────────────────────────
    with st.spinner("Checking market mood..."):
        mood = get_market_mood(interval, period)

    mood_signal = mood.get("signal", "UNKNOWN")
    mood_conf = mood.get("confidence", 0)
    mood_price = mood.get("last_price", 0)

    if mood_signal == "BUY":
        mood_icon = "▲"
        mood_text = "Bullish — Good time to look for buys"
    elif mood_signal == "SELL":
        mood_icon = "▼"
        mood_text = "Bearish — Be selective, reduce position sizes"
    else:
        mood_icon = "—"
        mood_text = "Neutral — Wait for clearer signals"

    mood_color = SIGNAL_COLORS.get(mood_signal, "#aaa")
    st.markdown(
        f"""
        <div style="
            background:{mood_color}12;
            border:1px solid {mood_color}44;
            border-left:4px solid {mood_color};
            border-radius:10px;
            padding:14px 20px;
            display:flex;
            align-items:center;
            gap:24px;
            margin-bottom:8px;
        ">
            <span style="font-size:1.8rem;font-weight:800;color:{mood_color};">{mood_icon} {mood_signal}</span>
            <span style="color:#bbb;font-size:0.95rem;">{mood_text}</span>
            <span style="margin-left:auto;color:#888;font-size:0.85rem;">
                Nifty 50 &nbsp;<b style="color:#f0f0f0;">₹{mood_price:,.2f}</b>
                &nbsp;·&nbsp; Confidence &nbsp;<b style="color:{mood_color};">{mood_conf}%</b>
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    # ── Scan ─────────────────────────────────────────────────────────────────
    with st.spinner(f"Scanning {len(TOP100)} stocks (Nifty 100)..."):
        all_results = scan_all_stocks(interval, period)

    buy_signals = [
        r for r in all_results
        if r.get("signal") == "BUY" and r.get("confidence", 0) >= min_confidence
    ]
    buy_signals.sort(key=lambda x: x["confidence"], reverse=True)

    # ── Summary row ──────────────────────────────────────────────────────────
    total_scanned = len(all_results)
    total_buys = len(buy_signals)

    c1, c2, c3 = st.columns(3)
    c1.metric("Stocks Scanned", total_scanned)
    c2.metric("BUY Opportunities", total_buys, delta=f"≥{min_confidence}% confidence")
    c3.metric("Scan Interval", interval.upper())

    st.divider()

    if not buy_signals:
        st.warning(
            f"No BUY signals found with confidence ≥ {min_confidence}%. "
            "Try lowering the confidence threshold or check again after market hours."
        )
    else:
        # ── Opportunity table ─────────────────────────────────────────────────
        st.subheader("🎯 Buy Opportunities")

        table_rows = []
        for r in buy_signals:
            price = r["last_price"]
            sl = r["stop_loss"]
            target = r["target"]
            risk = round(price - sl, 2)
            reward = round(target - price, 2)
            rr = round(reward / risk, 2) if risk > 0 else 0
            risk_pct = round((risk / price) * 100, 2)
            reward_pct = round((reward / price) * 100, 2)

            table_rows.append({
                "Stock":       r["name"],
                "Ticker":      r["ticker"],
                "Price":       f"₹{price:,.2f}",
                "Stop Loss":   f"₹{sl:,.2f}",
                "Target":      f"₹{target:,.2f}",
                "Risk %":      f"-{risk_pct}%",
                "Reward %":    f"+{reward_pct}%",
                "R:R":         f"1 : {rr}",
                "Confidence":  r["confidence"],
                "_price_raw":  price,
                "_sl_raw":     sl,
                "_target_raw": target,
                "_conf_raw":   r["confidence"],
            })

        df_table = pd.DataFrame(table_rows)

        # Display clean table (hide raw columns)
        display_cols = ["Stock", "Ticker", "Price", "Stop Loss", "Target",
                        "Risk %", "Reward %", "R:R", "Confidence"]

        st.dataframe(
            df_table[display_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Confidence": st.column_config.ProgressColumn(
                    "Confidence",
                    help="Signal strength (0–100)",
                    format="%d%%",
                    min_value=0,
                    max_value=100,
                ),
            },
        )

        st.divider()

        # ── Stock drill-down ──────────────────────────────────────────────────
        st.subheader("🔍 Stock Detail")

        names = [r["name"] for r in buy_signals]
        selected_name = st.selectbox("Select a stock to analyze", names)

        selected = next((r for r in buy_signals if r["name"] == selected_name), None)

        if selected and "df" in selected:
            sig = selected
            df = sig["df"]
            price = sig["last_price"]
            sl = sig["stop_loss"]
            target = sig["target"]
            risk = round(price - sl, 2)
            reward = round(target - price, 2)
            rr = round(reward / risk, 2) if risk > 0 else 0

            # Action card
            st.markdown(f"### {selected_name} — {sig['ticker']}")

            ma, mb, mc, md, me = st.columns(5)
            ma.metric("Entry Price", f"₹{price:,.2f}")
            mb.metric("Stop Loss", f"₹{sl:,.2f}", delta=f"-{round((price-sl)/price*100,1)}%", delta_color="inverse")
            mc.metric("Target", f"₹{target:,.2f}", delta=f"+{round((target-price)/price*100,1)}%")
            md.metric("Risk : Reward", f"1 : {rr}")
            me.metric("Confidence", f"{sig['confidence']}%")

            # Trade brief
            atr = float(df["ATR_14"].iloc[-1]) if "ATR_14" in df.columns else 0
            st.info(
                f"**Trade Setup** — Buy `{selected_name}` at ₹{price:,.2f}  |  "
                f"Stop Loss: ₹{sl:,.2f} (below)  |  "
                f"Target: ₹{target:,.2f} (above)  |  "
                f"ATR: {atr:.2f}"
            )

            # Indicator breakdown
            with st.expander("Indicator Breakdown", expanded=False):
                comp_rows = []
                for ind_name, v in sig["components"].items():
                    pts = v["points"]
                    comp_rows.append({
                        "Indicator": ind_name,
                        "Value":     str(v["value"]),
                        "Signal":    v["signal"],
                        "Points":    f"{pts:+d}",
                    })
                st.dataframe(pd.DataFrame(comp_rows), hide_index=True, use_container_width=True)

            # Full chart
            fig = build_stock_chart(df, sig, selected_name)
            st.plotly_chart(fig, use_container_width=True)

    # ── Custom stock search result ────────────────────────────────────────────
    custom_ticker = st.session_state.get("custom_ticker")
    custom_name   = st.session_state.get("custom_name", custom_ticker)
    if custom_ticker:
        st.divider()
        st.subheader(f"🔎 Custom Analysis: {custom_name}")
        with st.spinner(f"Fetching {custom_ticker}..."):
            custom_sig = get_signal_for(custom_ticker, interval, period)
        if custom_sig and "error" not in custom_sig:
            df_c   = custom_sig["df"]
            price  = custom_sig["last_price"]
            sl     = custom_sig["stop_loss"]
            target = custom_sig["target"]
            risk   = round(price - sl, 2)
            reward = round(target - price, 2)
            rr     = round(reward / risk, 2) if risk > 0 else 0

            ca, cb, cc, cd, ce = st.columns(5)
            ca.metric("Entry", f"₹{price:,.2f}")
            cb.metric("Stop Loss", f"₹{sl:,.2f}", delta=f"-{round((price-sl)/price*100,1)}%", delta_color="inverse")
            cc.metric("Target",    f"₹{target:,.2f}", delta=f"+{round((target-price)/price*100,1)}%")
            cd.metric("R:R",       f"1 : {rr}")
            ce.metric("Signal",    f"{custom_sig['signal']} {custom_sig['confidence']}%")

            signal_color = {"BUY": "#26a69a", "SELL": "#ef5350", "HOLD": "#ffa726"}.get(custom_sig["signal"], "#aaa")
            st.markdown(
                f'<div style="background:{signal_color}22;border-left:4px solid {signal_color};'
                f'padding:10px 16px;border-radius:6px;">'
                f'<b style="color:{signal_color}">{custom_sig["signal"]}</b> — '
                f'Entry ₹{price:,.2f} | SL ₹{sl:,.2f} | Target ₹{target:,.2f}</div>',
                unsafe_allow_html=True,
            )
            fig_c = build_stock_chart(df_c, custom_sig, custom_name)
            st.plotly_chart(fig_c, use_container_width=True)
        elif custom_sig and "error" in custom_sig:
            st.error(f"Could not load {custom_ticker}: {custom_sig['error']}")

    # ── All results summary ───────────────────────────────────────────────────
    with st.expander("📊 Full Scan Results (all stocks)", expanded=False):
        summary_rows = []
        for r in sorted(all_results, key=lambda x: x.get("confidence", 0), reverse=True):
            summary_rows.append({
                "Stock":      r.get("name", r.get("ticker", "?")),
                "Signal":     r.get("signal", "ERR"),
                "Confidence": r.get("confidence", 0),
                "Price":      f"₹{r['last_price']:,.2f}" if "last_price" in r else "—",
                "SL":         f"₹{r['stop_loss']:,.2f}" if "stop_loss" in r else "—",
                "Target":     f"₹{r['target']:,.2f}" if "target" in r else "—",
            })
        if summary_rows:
            st.dataframe(pd.DataFrame(summary_rows), hide_index=True, use_container_width=True)

    st.divider()
    st.caption(
        "Signals are generated from RSI, MACD, EMA trend, Bollinger Bands, Support/Resistance, and OBV. "
        "This is not financial advice. Always use a stop loss."
    )


if __name__ == "__main__":
    main()
