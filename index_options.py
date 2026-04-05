"""
Index Options Dashboard — NIFTY & BANKNIFTY
Buy the right CALL or PUT for an index at the right strike and expiry.
Covers both intraday and positional timeframes.
No short-selling. Buy-side only.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh

from tools.analyze_options import recommend_option
from tools.fetch_options_chain import fetch_options_chain, get_nearest_atm_strike
from tools.theme import inject_css, signal_badge, page_header

INDICES = {
    "Nifty 50":   "NIFTY",
    "Bank Nifty": "BANKNIFTY",
}

SIGNAL_COLOR = {"BUY": "#26a69a", "SELL": "#ef5350", "HOLD": "#ffa726"}
SIGNAL_EMOJI = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}


# ── Caching ────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def get_recommendation(symbol: str, expiry: str = None) -> dict:
    """Full pipeline: underlying signal + options chain → recommendation."""
    try:
        return recommend_option(symbol, style="both", expiry=expiry)
    except Exception as e:
        return {"error": str(e), "symbol": symbol}


@st.cache_data(ttl=300, show_spinner=False)
def get_chain(symbol: str, expiry: str = None) -> dict | None:
    """Fetch raw options chain for visualization."""
    try:
        return fetch_options_chain(symbol, expiry=expiry)
    except Exception as e:
        return None


# ── Option chain OI chart ──────────────────────────────────────────────────────

def build_oi_chart(chain_data: dict, spot: float, symbol: str, expiry: str) -> go.Figure:
    """
    Back-to-back bar chart of CE vs PE open interest around ATM.
    Shows where the market has placed its bets.
    """
    df = chain_data["chain"]
    df = df[df["expiry"] == expiry].copy()
    if df.empty:
        return None

    atm = get_nearest_atm_strike(spot, symbol)
    # Show ±10 strikes around ATM
    interval = {"NIFTY": 50, "BANKNIFTY": 100}.get(symbol, 50)
    lo = atm - interval * 10
    hi = atm + interval * 10
    df = df[(df["strike"] >= lo) & (df["strike"] <= hi)]

    if df.empty:
        return None

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df["strike"].astype(str),
        x=-df["PE_oi"],  # negative = goes left
        name="PUT OI",
        orientation="h",
        marker_color="rgba(239,83,80,0.75)",
    ))
    fig.add_trace(go.Bar(
        y=df["strike"].astype(str),
        x=df["CE_oi"],
        name="CALL OI",
        orientation="h",
        marker_color="rgba(38,166,154,0.75)",
    ))

    # ATM line — use add_shape so it works with a categorical string y-axis
    atm_str = str(atm)
    if atm_str in df["strike"].astype(str).values:
        fig.add_shape(
            type="line",
            xref="paper", x0=0, x1=1,
            yref="y",    y0=atm_str, y1=atm_str,
            line=dict(color="white", width=1.5, dash="dash"),
        )
        fig.add_annotation(
            x=1, xref="paper",
            y=atm_str, yref="y",
            text=f"ATM {atm}",
            showarrow=False,
            xanchor="left", font=dict(color="white", size=11),
        )

    fig.update_layout(
        barmode="overlay",
        title=f"Open Interest — {symbol} ({expiry})",
        template="plotly_dark",
        height=500,
        xaxis_title="Open Interest (← PUT | CALL →)",
        yaxis_title="Strike",
        legend=dict(orientation="h", y=1.05),
        margin=dict(l=20, r=20, t=50, b=30),
        xaxis=dict(tickformat=","),
    )
    return fig


def build_premium_chart(rec: dict, style: str) -> go.Figure:
    """
    Simple gauge showing the premium target vs stop-loss range.
    Helps visualize R:R on the option itself.
    """
    r = rec["recommendations"].get(style)
    if not r or "error" in r:
        return None

    premium = r["premium"]
    sl = r["stop_loss"]
    target = r["target"]

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=premium,
        title={"text": f"{style.title()} Premium ₹{premium}"},
        gauge={
            "axis": {"range": [sl * 0.8, target * 1.1]},
            "bar": {"color": "#2196f3"},
            "steps": [
                {"range": [sl * 0.8, sl], "color": "rgba(239,83,80,0.3)"},
                {"range": [sl, premium], "color": "rgba(239,83,80,0.15)"},
                {"range": [premium, target], "color": "rgba(38,166,154,0.15)"},
                {"range": [target, target * 1.1], "color": "rgba(38,166,154,0.3)"},
            ],
            "threshold": {
                "line": {"color": "#ef5350", "width": 2},
                "thickness": 0.75,
                "value": sl,
            },
        },
    ))
    fig.update_layout(
        template="plotly_dark",
        height=250,
        margin=dict(l=20, r=20, t=40, b=10),
    )
    return fig


# ── Render one recommendation card ────────────────────────────────────────────

def render_rec_card(rec_data: dict, style: str, symbol: str):
    """Render intraday or positional recommendation."""
    recs = rec_data.get("recommendations", {})
    r = recs.get(style)

    if not r:
        st.info(f"No {style} recommendation available.")
        return

    if "error" in r:
        st.error(f"{style.title()} Error: {r['error']}")
        return

    option_type = r["option_type"]
    action_color = "#26a69a" if option_type == "CALL" else "#ba68c8"

    # Action badge
    st.markdown(
        f"""
        <div style="background:{action_color}22; border-left:4px solid {action_color};
                    padding:12px 16px; border-radius:6px; margin-bottom:12px;">
            <span style="color:{action_color}; font-size:1.3em; font-weight:700;">
                BUY {option_type}
            </span>
            <span style="color:#aaa; margin-left:12px; font-size:0.9em;">
                {r['option']}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Strike", f"₹{r['strike']:,}")
    c2.metric("Expiry", r["expiry"])
    c3.metric("Premium (Entry)", f"₹{r['premium']}")
    c4.metric("Lot Size", r["lot_size"])

    c5, c6, c7, c8 = st.columns(4)
    c5.metric(
        "Stop Loss",
        f"₹{r['stop_loss']}",
        delta=f"-{r['sl_pct']}%  (-{r['sl_points']} pts)",
        delta_color="inverse",
    )
    c6.metric(
        "Target",
        f"₹{r['target']}",
        delta=f"+{r['target_pct']}%  (+{r['target_points']} pts)",
    )
    c7.metric("Capital / Lot", f"₹{r['capital_1_lot']:,.0f}")
    c8.metric("IV", f"{r['iv']}%")

    c9, c10, c11 = st.columns(3)
    c9.metric("Max Loss / Lot", f"₹{r['max_loss_1_lot']:,.0f}", delta_color="inverse")
    c10.metric("Max Profit / Lot", f"₹{r['max_profit_1_lot']:,.0f}")
    rr = round(r["max_profit_1_lot"] / r["max_loss_1_lot"], 2) if r["max_loss_1_lot"] > 0 else 0
    c11.metric("Reward : Risk", f"1 : {rr}")

    # Premium gauge
    gauge = build_premium_chart(rec_data, style)
    if gauge:
        st.plotly_chart(gauge, use_container_width=True)

    st.caption(
        f"**How to read:** Entry = buy at ₹{r['premium']}. "
        f"Exit (SL) if premium drops to ₹{r['stop_loss']} ({r['sl_pct']}% loss on premium). "
        f"Book profit at ₹{r['target']} ({r['target_pct']}% gain on premium)."
    )


# ── Render one index tab ───────────────────────────────────────────────────────

def render_index_tab(label: str, symbol: str):
    """Full dashboard for one index."""

    # ── Step 1: fetch nearest expiry chain just to get the expiry list ────────
    with st.spinner(f"Loading {label} expiry dates..."):
        meta = get_chain(symbol)  # fast, cached; used only for expiry_dates

    if meta is None:
        st.error(f"Could not load {label} options chain.")
        return

    expiry_dates = meta.get("expiry_dates", [])

    # ── Expiry selector at the top ────────────────────────────────────────────
    if expiry_dates:
        selected_expiry = st.selectbox(
            "Select Expiry",
            expiry_dates,
            index=0,
            key=f"expiry_main_{symbol}",
            help="Intraday tab uses this expiry. Positional tab uses the next expiry after this.",
        )
    else:
        st.warning("No expiry dates found.")
        return

    # ── Step 2: fetch chain for the SELECTED expiry (for OI chart) ────────────
    with st.spinner(f"Loading chain for {selected_expiry}..."):
        chain_data = get_chain(symbol, selected_expiry)

    # ── Step 3: full recommendation for chosen expiry ─────────────────────────
    with st.spinner(f"Analysing {label} for {selected_expiry}..."):
        rec = get_recommendation(symbol, selected_expiry)

    # ── Error state ───────────────────────────────────────────────────────────
    if "error" in rec:
        st.error(f"Could not load {label} data: {rec['error']}")
        st.info("NSE might be blocking requests. Wait a few seconds and click Refresh.")
        return

    signal = rec["underlying_signal"]
    confidence = rec["confidence"]
    spot = rec["spot"]
    option_type = rec.get("option_type", "N/A")
    pcr = rec.get("pcr", {})
    max_pain = rec.get("max_pain")
    timestamp = rec.get("timestamp", "")

    # ── Summary row ───────────────────────────────────────────────────────────
    sig_color = SIGNAL_COLOR.get(signal, "#aaa")
    sig_emoji = SIGNAL_EMOJI.get(signal, "⚪")

    st.markdown(
        signal_badge(signal, confidence, f"Buy {option_type} · {timestamp}"),
        unsafe_allow_html=True,
    )

    if signal == "HOLD":
        st.warning(
            "Underlying trend is HOLD — conflicting signals. "
            "No clear edge for options. Wait for a stronger directional move before entering."
        )
        return

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(f"{label} Spot", f"₹{spot:,.2f}")
    c2.metric("Direction", f"{'📈 Bullish' if signal == 'BUY' else '📉 Bearish'}")
    c3.metric("Confidence", f"{confidence}%")
    c4.metric(
        "PCR",
        f"{pcr.get('pcr', '—')}",
        help="Put-Call Ratio: >1.2 = Bullish, <0.8 = Bearish",
    )
    c5.metric("Max Pain", f"₹{max_pain:,.0f}" if max_pain else "—")

    pcr_signal = pcr.get("signal", "")
    if pcr_signal:
        st.caption(f"PCR Signal: {pcr_signal}")

    st.divider()

    # ── Intraday vs Positional ────────────────────────────────────────────────
    tab_intra, tab_pos = st.tabs(["📅 Intraday (Near Expiry)", "📆 Positional (Next Expiry)"])

    with tab_intra:
        render_rec_card(rec, "intraday", symbol)

    with tab_pos:
        render_rec_card(rec, "positional", symbol)

    st.divider()

    # ── Option chain OI chart ─────────────────────────────────────────────────
    st.subheader("Open Interest — Where the Market Is Positioned")

    oi_fig = build_oi_chart(chain_data, spot, symbol, selected_expiry)
    if oi_fig:
        st.plotly_chart(oi_fig, use_container_width=True)
        st.caption(
            "Green bars = CALL open interest (bearish writers). "
            "Red bars = PUT open interest (bullish writers). "
            "High OI at a strike = strong support/resistance."
        )
    else:
        st.info(f"No OI data available for {selected_expiry}.")

    # ── Signal components ─────────────────────────────────────────────────────
    with st.expander("🔬 Signal Breakdown (underlying trend indicators)", expanded=False):
        components = rec.get("signal_components", {})
        if components:
            rows = [
                {
                    "Indicator": name,
                    "Value":     str(v["value"]),
                    "Signal":    v["signal"],
                    "Points":    f"{v['points']:+d}",
                }
                for name, v in components.items()
            ]
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        else:
            st.info("No component data.")

    # ── ATM option chain table ─────────────────────────────────────────────────
    with st.expander("📋 ATM Option Chain (±10 strikes)", expanded=False):
        df = chain_data["chain"]
        chain_expiry = st.selectbox(
            "Expiry",
            expiry_dates[:8] if expiry_dates else [],
            index=expiry_dates.index(selected_expiry) if selected_expiry in expiry_dates else 0,
            key=f"expiry_chain_{symbol}",
        )
        if chain_expiry:
            if True:
                atm = get_nearest_atm_strike(spot, symbol)
                interval = {"NIFTY": 50, "BANKNIFTY": 100}.get(symbol, 50)
                lo, hi = atm - interval * 10, atm + interval * 10
                sub = df[(df["expiry"] == chain_expiry) & df["strike"].between(lo, hi)].copy()

                if not sub.empty:
                    display = sub[[
                        "strike",
                        "CE_ltp", "CE_iv", "CE_oi", "CE_volume",
                        "PE_ltp", "PE_iv", "PE_oi", "PE_volume",
                    ]].rename(columns={
                        "strike": "Strike",
                        "CE_ltp": "CE LTP", "CE_iv": "CE IV%",
                        "CE_oi": "CE OI", "CE_volume": "CE Vol",
                        "PE_ltp": "PE LTP", "PE_iv": "PE IV%",
                        "PE_oi": "PE OI", "PE_volume": "PE Vol",
                    })
                    st.dataframe(display, hide_index=True, use_container_width=True)
                else:
                    st.info(f"No chain data for {chain_expiry}.")


# ── App entry point ────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="Index Options — NIFTY & BANKNIFTY",
        page_icon="assets/favicon.svg",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_css()

    # ── Live auto-refresh ─────────────────────────────────────────────────────
    with st.sidebar:
        st.subheader("⚡ Live Refresh")
        refresh_options = {"Off": 0, "30 sec": 30, "1 min": 60, "2 min": 120, "5 min": 300}
        selected_refresh = st.selectbox("Auto-refresh interval", list(refresh_options.keys()), index=2)
        refresh_secs = refresh_options[selected_refresh]
        if refresh_secs > 0:
            count = st_autorefresh(interval=refresh_secs * 1000, key="index_autorefresh")
            if count > 0:
                st.cache_data.clear()
            st.caption(f"Refresh #{count} · every {selected_refresh}")
        else:
            st.caption("Auto-refresh is off.")
        if st.button("🔄 Refresh Now", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    page_header(
        "Index Options Dashboard",
        "Buy CALL or PUT on NIFTY & BANKNIFTY · Intraday + Positional · Entry on premium + SL + Target",
    )

    tab_nifty, tab_banknifty = st.tabs(["Nifty 50", "Bank Nifty"])

    with tab_nifty:
        render_index_tab("Nifty 50", "NIFTY")

    with tab_banknifty:
        render_index_tab("Bank Nifty", "BANKNIFTY")

    st.divider()
    st.caption(
        "Signal is based on daily trend (RSI, MACD, EMA, Bollinger, OBV). "
        "Options data is live from NSE. "
        "SL and Target are on the premium — not the underlying price. "
        "Not financial advice. Always use a stop loss."
    )


if __name__ == "__main__":
    main()
