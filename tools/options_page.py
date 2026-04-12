"""
Index Options page content — called by dashboard.py for single-page routing.
All rendering functions + render_page() entry point.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh

from tools.analyze_options import recommend_option
from tools.fetch_options_chain import fetch_options_chain, get_nearest_atm_strike
from tools.theme import signal_badge, page_header
from tools.fetch_stock_data import fetch_ohlcv
from tools.compute_indicators import compute_all

INDICES = {
    "Nifty 50":   "NIFTY",
    "Bank Nifty": "BANKNIFTY",
}

OHLCV_TICKER = {
    "NIFTY":      "^NSEI",
    "BANKNIFTY":  "^NSEBANK",
    "MIDCPNIFTY": "^NSEMDCP50",
}

SIGNAL_COLOR = {"BUY": "#26a69a", "SELL": "#ef5350", "HOLD": "#ffa726"}
SIGNAL_EMOJI = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}


# ── Caching ────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def get_recommendation(symbol: str, expiry: str = None) -> dict:
    try:
        return recommend_option(symbol, style="both", expiry=expiry)
    except Exception as e:
        return {"error": str(e), "symbol": symbol}


@st.cache_data(ttl=300, show_spinner=False)
def get_chain(symbol: str, expiry: str = None) -> dict:
    try:
        return fetch_options_chain(symbol, expiry=expiry)
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=300, show_spinner=False)
def get_ohlcv(ticker: str) -> pd.DataFrame:
    try:
        df = fetch_ohlcv(ticker, interval="1d", period="3mo")
        if df is not None and not df.empty:
            return compute_all(df)
    except Exception:
        pass
    return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _x_labels(df: pd.DataFrame) -> list:
    idx = df.index
    try:
        if len(idx) > 0 and (idx[0].hour != 0 or idx[0].minute != 0):
            return [ts.strftime('%b %d %H:%M') for ts in idx]
    except AttributeError:
        pass
    return [ts.strftime('%b %d') if hasattr(ts, 'strftime') else str(ts) for ts in idx]


# ── Price Chart ────────────────────────────────────────────────────────────────

def build_price_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    xlabels = _x_labels(df)

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.03,
    )

    fig.add_trace(go.Candlestick(
        x=xlabels,
        open=df["Open"], high=df["High"],
        low=df["Low"],  close=df["Close"],
        name="Price",
        increasing_line_color="#26a69a",
        decreasing_line_color="#ef5350",
        showlegend=False,
    ), row=1, col=1)

    if "BB_upper" in df.columns and "BB_lower" in df.columns:
        fig.add_trace(go.Scattergl(
            x=xlabels, y=df["BB_upper"],
            name="BB Upper",
            line=dict(color="rgba(150,150,255,0.5)", width=1),
            showlegend=True,
        ), row=1, col=1)
        fig.add_trace(go.Scattergl(
            x=xlabels, y=df["BB_lower"],
            name="BB Lower",
            line=dict(color="rgba(150,150,255,0.5)", width=1),
            fill="tonexty",
            fillcolor="rgba(150,150,255,0.07)",
            showlegend=True,
        ), row=1, col=1)

    for col, color, label in [
        ("EMA_9",  "#FFD700", "EMA 9"),
        ("EMA_21", "#FF8C00", "EMA 21"),
        ("EMA_50", "#00BFFF", "EMA 50"),
        ("EMA_200","#FF69B4", "EMA 200"),
    ]:
        if col in df.columns:
            fig.add_trace(go.Scattergl(
                x=xlabels, y=df[col],
                name=label,
                line=dict(color=color, width=1.2),
            ), row=1, col=1)

    colors = ["#26a69a" if c >= o else "#ef5350"
              for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(
        x=xlabels, y=df["Volume"],
        name="Volume",
        marker_color=colors,
        opacity=0.6,
        showlegend=False,
    ), row=2, col=1)

    fig.update_layout(
        template="plotly_dark",
        height=480,
        xaxis_rangeslider_visible=False,
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(orientation="h", y=1.02, x=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        title=dict(text=f"{symbol} — 3-Month Daily Chart", font=dict(size=14)),
        bargap=0,
        bargroupgap=0,
        dragmode="pan",
        uirevision=f"price_{symbol}",
        transition=dict(duration=0, easing="linear"),
    )
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.05)", fixedrange=False)
    fig.update_xaxes(
        type="category",
        gridcolor="rgba(255,255,255,0.05)",
        nticks=7,
        tickangle=0,
        fixedrange=False,
    )
    return fig


# ── Premium-by-Expiry Chart ────────────────────────────────────────────────────

def build_premium_by_expiry_chart(
    chain_data: dict, spot: float, symbol: str,
    recommended_expiry: str, recommended_type: str,
) -> go.Figure:
    df_full = chain_data.get("chain")
    expiry_dates = chain_data.get("expiry_dates", [])
    if df_full is None or df_full.empty or not expiry_dates:
        return None

    atm = get_nearest_atm_strike(spot, symbol)
    shown_expiries = expiry_dates[:8]

    ce_premiums, pe_premiums = [], []
    for exp in shown_expiries:
        sub = df_full[(df_full["expiry"] == exp) & (df_full["strike"] == atm)]
        ce_premiums.append(float(sub["CE_ltp"].values[0]) if not sub.empty else 0)
        pe_premiums.append(float(sub["PE_ltp"].values[0]) if not sub.empty else 0)

    star_ce = [None] * len(shown_expiries)
    star_pe = [None] * len(shown_expiries)
    if recommended_expiry in shown_expiries:
        idx = shown_expiries.index(recommended_expiry)
        if recommended_type == "CALL":
            star_ce[idx] = ce_premiums[idx]
        else:
            star_pe[idx] = pe_premiums[idx]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=shown_expiries, y=ce_premiums,
        name="CE (Call) ATM Premium",
        marker_color="rgba(38,166,154,0.8)",
    ))
    fig.add_trace(go.Bar(
        x=shown_expiries, y=pe_premiums,
        name="PE (Put) ATM Premium",
        marker_color="rgba(239,83,80,0.8)",
    ))

    if recommended_expiry in shown_expiries:
        idx = shown_expiries.index(recommended_expiry)
        val = ce_premiums[idx] if recommended_type == "CALL" else pe_premiums[idx]
        fig.add_annotation(
            x=recommended_expiry, y=val,
            text="⭐ Pick",
            showarrow=True, arrowhead=2,
            arrowcolor="#ffd700", font=dict(color="#ffd700", size=13),
            yshift=10,
        )

    fig.update_layout(
        template="plotly_dark",
        title=f"ATM ({atm}) Premium Across Expiries — {symbol}",
        barmode="group",
        height=340,
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_title="Expiry",
        yaxis_title="Premium ₹",
        legend=dict(orientation="h", y=1.08),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ── OI Chart ──────────────────────────────────────────────────────────────────

def build_oi_chart(chain_data: dict, spot: float, symbol: str, expiry: str) -> go.Figure:
    df = chain_data["chain"]
    df = df[df["expiry"] == expiry].copy()
    if df.empty:
        return None

    atm = get_nearest_atm_strike(spot, symbol)
    interval = {"NIFTY": 50, "BANKNIFTY": 100}.get(symbol, 50)
    lo = atm - interval * 10
    hi = atm + interval * 10
    df = df[(df["strike"] >= lo) & (df["strike"] <= hi)]

    if df.empty:
        return None

    if df["CE_oi"].sum() == 0 and df["PE_oi"].sum() == 0:
        return None

    df = df.sort_values("strike", ascending=False)
    strike_labels = [str(s) for s in df["strike"]]
    ce_oi = df["CE_oi"].tolist()
    pe_oi = df["PE_oi"].tolist()
    atm_label = str(atm)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=strike_labels,
        x=[-v for v in pe_oi],
        name="PUT OI",
        orientation="h",
        marker_color="rgba(239,83,80,0.85)",
    ))
    fig.add_trace(go.Bar(
        y=strike_labels,
        x=ce_oi,
        name="CALL OI",
        orientation="h",
        marker_color="rgba(38,166,154,0.85)",
    ))

    if atm_label in strike_labels:
        fig.add_shape(
            type="line",
            xref="paper", x0=0, x1=1,
            yref="y",    y0=atm_label, y1=atm_label,
            line=dict(color="white", width=1.5, dash="dash"),
        )
        fig.add_annotation(
            x=1, xref="paper",
            y=atm_label, yref="y",
            text=f"ATM {atm}",
            showarrow=False,
            xanchor="left", font=dict(color="white", size=11),
        )

    n = len(strike_labels)
    chart_height = max(420, n * 24)
    fig.update_layout(
        barmode="overlay",
        title=f"Open Interest — {symbol} ({expiry})",
        template="plotly_dark",
        height=chart_height,
        xaxis_title="Open Interest (← PUT | CALL →)",
        yaxis_title="Strike",
        legend=dict(orientation="h", y=1.05),
        margin=dict(l=20, r=80, t=50, b=30),
        xaxis=dict(tickformat=","),
        yaxis=dict(range=[-0.5, n - 0.5]),
    )
    return fig


# ── Premium gauge ──────────────────────────────────────────────────────────────

def build_premium_chart(rec: dict, style: str) -> go.Figure:
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
                {"range": [sl * 0.8, sl],       "color": "rgba(239,83,80,0.3)"},
                {"range": [sl, premium],         "color": "rgba(239,83,80,0.15)"},
                {"range": [premium, target],     "color": "rgba(38,166,154,0.15)"},
                {"range": [target, target * 1.1],"color": "rgba(38,166,154,0.3)"},
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


# ── Recommendation card ────────────────────────────────────────────────────────

def render_rec_card(rec_data: dict, style: str, symbol: str):
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
        "Stop Loss", f"₹{r['stop_loss']}",
        delta=f"-{r['sl_pct']}%  (-{r['sl_points']} pts)",
        delta_color="inverse",
    )
    c6.metric(
        "Target", f"₹{r['target']}",
        delta=f"+{r['target_pct']}%  (+{r['target_points']} pts)",
    )
    c7.metric("Capital / Lot", f"₹{r['capital_1_lot']:,.0f}")
    c8.metric("IV", f"{r['iv']}%")

    c9, c10, c11 = st.columns(3)
    c9.metric("Max Loss / Lot",   f"₹{r['max_loss_1_lot']:,.0f}",   delta_color="inverse")
    c10.metric("Max Profit / Lot", f"₹{r['max_profit_1_lot']:,.0f}")
    rr = round(r["max_profit_1_lot"] / r["max_loss_1_lot"], 2) if r["max_loss_1_lot"] > 0 else 0
    c11.metric("Reward : Risk", f"1 : {rr}")

    gauge = build_premium_chart(rec_data, style)
    if gauge:
        st.plotly_chart(gauge, width="stretch")

    st.caption(
        f"**How to read:** Entry = buy at ₹{r['premium']}. "
        f"Exit (SL) if premium drops to ₹{r['stop_loss']} ({r['sl_pct']}% loss). "
        f"Book profit at ₹{r['target']} ({r['target_pct']}% gain)."
    )


# ── Written analysis summary ───────────────────────────────────────────────────

def render_analysis_summary(rec: dict, symbol: str):
    signal    = rec.get("underlying_signal", "HOLD")
    conf      = rec.get("confidence", 0)
    spot      = rec.get("spot", 0)
    opt_type  = rec.get("option_type", "—")
    pcr_data  = rec.get("pcr", {})
    pcr_val   = pcr_data.get("pcr", "—")
    pcr_sig   = pcr_data.get("signal", "")
    max_pain  = rec.get("max_pain")
    timestamp = rec.get("timestamp", "")
    recs      = rec.get("recommendations", {})
    intra     = recs.get("intraday", {})
    pos       = recs.get("positional", {})
    comps     = rec.get("signal_components", {})

    indicator_lines = []
    for name, v in comps.items():
        indicator_lines.append(f"{name}: **{v.get('signal', '—')}**")
    indicator_str = " · ".join(indicator_lines) if indicator_lines else "N/A"

    intra_action = ""
    if intra and "error" not in intra:
        intra_action = (
            f"**{intra.get('option', '—')}** expiring **{intra.get('expiry', '—')}**\n"
            f"- Entry: ₹{intra.get('premium', '—')} &nbsp;|&nbsp; "
            f"Stop Loss: ₹{intra.get('stop_loss', '—')} (–{intra.get('sl_pct', '—')}%) &nbsp;|&nbsp; "
            f"Target: ₹{intra.get('target', '—')} (+{intra.get('target_pct', '—')}%)\n"
            f"- Capital for 1 lot ({intra.get('lot_size', '—')} units): "
            f"₹{intra.get('capital_1_lot', 0):,.0f} &nbsp;|&nbsp; "
            f"Max Loss: ₹{intra.get('max_loss_1_lot', 0):,.0f} &nbsp;|&nbsp; "
            f"Max Profit: ₹{intra.get('max_profit_1_lot', 0):,.0f}"
        )

    pos_action = ""
    if pos and "error" not in pos:
        pos_action = (
            f"**{pos.get('option', '—')}** expiring **{pos.get('expiry', '—')}**\n"
            f"- Entry: ₹{pos.get('premium', '—')} &nbsp;|&nbsp; "
            f"Stop Loss: ₹{pos.get('stop_loss', '—')} (–{pos.get('sl_pct', '—')}%) &nbsp;|&nbsp; "
            f"Target: ₹{pos.get('target', '—')} (+{pos.get('target_pct', '—')}%)"
        )

    try:
        pcr_num = float(pcr_val)
        if pcr_num > 1.2:
            pcr_interp = f"PCR = {pcr_val} → above 1.2, puts heavily written = **bullish bias**"
        elif pcr_num < 0.8:
            pcr_interp = f"PCR = {pcr_val} → below 0.8, calls heavily written = **bearish bias**"
        else:
            pcr_interp = f"PCR = {pcr_val} → neutral zone (0.8–1.2)"
    except (TypeError, ValueError):
        pcr_interp = f"PCR = {pcr_val} ({pcr_sig})"

    max_pain_line = (
        f"Max pain at ₹{max_pain:,.0f} → "
        f"{'spot ({:.0f}) above max pain, sellers under pressure'.format(spot) if spot > (max_pain or 0) else 'spot ({:.0f}) below max pain, buyers under pressure'.format(spot)}"
        if max_pain else "Max pain: N/A"
    )

    direction_word = "BULLISH" if signal == "BUY" else "BEARISH" if signal == "SELL" else "NEUTRAL"
    signal_color   = "#26a69a" if signal == "BUY" else "#ef5350" if signal == "SELL" else "#ffa726"
    call_or_put    = "CALL" if signal == "BUY" else "PUT" if signal == "SELL" else "—"

    summary_md = f"""
<div style="background:rgba(255,255,255,0.04); border-left:4px solid {signal_color};
            padding:18px 20px; border-radius:8px; margin-bottom:8px; line-height:1.75;">

<span style="font-size:1.05em; font-weight:700; color:{signal_color};">
📍 Trade Analysis — {symbol} &nbsp;·&nbsp; {timestamp}
</span>

---

**Underlying Trend: {direction_word} ({conf}% confidence)**

{indicator_str}

---

**🎯 Intraday Trade (Near Expiry) — Buy {call_or_put}**

{intra_action if intra_action else "_No intraday recommendation (HOLD or data unavailable)_"}

**📆 Positional Trade (Next Expiry) — Buy {call_or_put}**

{pos_action if pos_action else "_No positional recommendation_"}

---

**Why {call_or_put}?**
- {pcr_interp}
- {max_pain_line}
- Signal consensus favours **{direction_word.lower()}** → buy **{call_or_put}**

</div>
"""
    st.markdown(summary_md, unsafe_allow_html=True)


# ── Render one index tab ───────────────────────────────────────────────────────

def render_index_tab(label: str, symbol: str):
    ticker = OHLCV_TICKER.get(symbol, "^NSEI")
    with st.spinner(f"Loading {label} price chart..."):
        price_df = get_ohlcv(ticker)

    if price_df is not None and not price_df.empty:
        fig_price = build_price_chart(price_df, symbol)
        st.plotly_chart(fig_price, width="stretch")
    else:
        st.warning(f"Could not load price data for {label}.")

    st.divider()

    with st.spinner(f"Loading {label} expiry dates..."):
        meta = get_chain(symbol)

    if meta is None or "error" in meta:
        err_msg = (meta or {}).get("error", "Unknown error")
        st.error(f"Could not load {label} options chain: {err_msg}")
        st.info("Angel One session may have expired. Click **Reset Session** in the sidebar and **Refresh Now**.")
        return

    expiry_dates = meta.get("expiry_dates", [])
    if not expiry_dates:
        st.warning("No expiry dates found.")
        return

    selected_expiry = st.selectbox(
        "Select Expiry",
        expiry_dates,
        index=0,
        key=f"expiry_main_{symbol}",
        help="Intraday tab uses this expiry. Positional tab uses the next expiry after this.",
    )

    with st.spinner(f"Loading chain for {selected_expiry}..."):
        chain_data = get_chain(symbol, selected_expiry)

    with st.spinner(f"Analysing {label} for {selected_expiry}..."):
        rec = get_recommendation(symbol, selected_expiry)

    if "error" in rec:
        st.error(f"Could not load {label} data: {rec['error']}")
        return

    signal     = rec["underlying_signal"]
    confidence = rec["confidence"]
    spot       = rec["spot"]
    option_type = rec.get("option_type", "N/A")
    pcr        = rec.get("pcr", {})
    max_pain   = rec.get("max_pain")
    timestamp  = rec.get("timestamp", "")

    st.markdown(
        signal_badge(signal, confidence, f"Buy {option_type} · {timestamp}"),
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(f"{label} Spot", f"₹{spot:,.2f}")
    c2.metric("Direction", f"{'📈 Bullish' if signal == 'BUY' else '📉 Bearish' if signal == 'SELL' else '➡️ Neutral'}")
    c3.metric("Confidence", f"{confidence}%")
    c4.metric("PCR", f"{pcr.get('pcr', '—')}", help="Put-Call Ratio: >1.2 = Bullish, <0.8 = Bearish")
    c5.metric("Max Pain", f"₹{max_pain:,.0f}" if max_pain else "—")

    st.divider()

    if signal == "HOLD":
        st.warning(
            "Underlying trend is HOLD — conflicting signals. "
            "No clear edge for options. Wait for a stronger directional move."
        )
        return

    with st.expander("📍 Trade Analysis & Rationale", expanded=True):
        render_analysis_summary(rec, symbol)

    st.divider()

    tab_intra, tab_pos = st.tabs(["📅 Intraday (Near Expiry)", "📆 Positional (Next Expiry)"])
    with tab_intra:
        render_rec_card(rec, "intraday", symbol)
    with tab_pos:
        render_rec_card(rec, "positional", symbol)

    st.divider()

    st.subheader("💰 Call vs Put Premium Across Expiries (ATM)")
    prem_fig = build_premium_by_expiry_chart(
        chain_data=meta,
        spot=spot,
        symbol=symbol,
        recommended_expiry=selected_expiry,
        recommended_type=option_type,
    )
    if prem_fig:
        st.plotly_chart(prem_fig, width="stretch")
        st.caption(
            "Teal = CALL premium · Red = PUT premium · Both at ATM strike. "
            "⭐ marks the recommended trade expiry."
        )
    else:
        st.info("Not enough data for premium chart. Try during market hours.")

    st.divider()

    st.subheader("📊 Open Interest — Where the Market Is Positioned")
    chain_spot = chain_data.get("underlying_value", spot)
    oi_fig = build_oi_chart(chain_data, chain_spot, symbol, selected_expiry)
    if oi_fig:
        st.plotly_chart(oi_fig, width="stretch")
        st.caption(
            "Green bars = CALL open interest (bearish writers). "
            "Red bars = PUT open interest (bullish writers). "
            "High OI at a strike = strong support/resistance."
        )
    else:
        st.warning(
            f"OI data unavailable for {selected_expiry}. "
            "This usually means the Angel One session has stale data — "
            "click **Refresh Now** in the sidebar to reload."
        )

    with st.expander("🔬 Signal Breakdown (underlying trend indicators)", expanded=False):
        components = rec.get("signal_components", {})
        if components:
            rows = [
                {"Indicator": name, "Value": str(v["value"]),
                 "Signal": v["signal"], "Points": f"{v['points']:+d}"}
                for name, v in components.items()
            ]
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        else:
            st.info("No component data.")

    with st.expander("📋 Full Option Chain Table (ATM ± 10 strikes)", expanded=False):
        df_all = chain_data.get("chain", pd.DataFrame())
        chain_expiry = st.selectbox(
            "Expiry",
            expiry_dates[:8] if expiry_dates else [],
            index=expiry_dates.index(selected_expiry) if selected_expiry in expiry_dates else 0,
            key=f"expiry_chain_{symbol}",
        )
        if chain_expiry and not df_all.empty:
            atm  = get_nearest_atm_strike(spot, symbol)
            intv = {"NIFTY": 50, "BANKNIFTY": 100}.get(symbol, 50)
            lo, hi = atm - intv * 10, atm + intv * 10
            sub = df_all[
                (df_all["expiry"] == chain_expiry) &
                df_all["strike"].between(lo, hi)
            ].copy()

            if not sub.empty:
                display = sub[[
                    "strike",
                    "CE_ltp", "CE_iv", "CE_oi", "CE_volume",
                    "PE_ltp", "PE_iv", "PE_oi", "PE_volume",
                ]].rename(columns={
                    "strike":     "Strike",
                    "CE_ltp":     "CE LTP",  "CE_iv": "CE IV%",
                    "CE_oi":      "CE OI",   "CE_volume": "CE Vol",
                    "PE_ltp":     "PE LTP",  "PE_iv": "PE IV%",
                    "PE_oi":      "PE OI",   "PE_volume": "PE Vol",
                })

                def highlight_atm(row):
                    return (["background-color: rgba(255,200,0,0.12)"] * len(row)
                            if row["Strike"] == atm else [""] * len(row))

                st.dataframe(
                    display.style.apply(highlight_atm, axis=1),
                    hide_index=True,
                    width="stretch",
                )
            else:
                st.info(f"No chain data for {chain_expiry}.")


# ── Page entry point ───────────────────────────────────────────────────────────

def render_page():
    """Render the full Index Options dashboard (called from dashboard.py routing)."""
    with st.sidebar:
        st.divider()
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

        if st.button("🔄 Refresh Now", key="opts_refresh_now", type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        if st.button("🔑 Reset Angel One Session", key="opts_reset_session", type="primary", use_container_width=True):
            from tools.angel_auth import reset_session
            reset_session()
            st.cache_data.clear()
            st.rerun()

    page_header(
        "Index Options Dashboard",
        "NIFTY · BANKNIFTY · MIDCPNIFTY · Price chart · Option chain · Intraday + Positional trade ideas",
    )

    tab_nifty, tab_banknifty, tab_midcp = st.tabs(["Nifty 50", "Bank Nifty", "MidCap Select"])
    with tab_nifty:
        render_index_tab("Nifty 50", "NIFTY")
    with tab_banknifty:
        render_index_tab("Bank Nifty", "BANKNIFTY")
    with tab_midcp:
        render_index_tab("MidCap Select", "MIDCPNIFTY")

    st.divider()
    st.caption(
        "Signal based on daily trend (RSI, MACD, EMA, Bollinger, OBV). "
        "Options data live from NSE via Angel One. "
        "SL and Target are on the premium — not the underlying price."
    )
