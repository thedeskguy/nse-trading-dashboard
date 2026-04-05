"""
Indian Mutual Funds Dashboard
Browse, compare, and get recommendations for Indian MFs.
Run: streamlit run mutual_funds_dashboard.py
"""

import sys
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

sys.path.insert(0, ".")
from tools.fetch_mutual_funds import (
    POPULAR_FUNDS, RISK_PROFILE,
    build_funds_dataframe, get_nav_history, search_funds,
    calculate_returns, score_fund, get_recommendation,
    fetch_fund_nav,
)
from tools.theme import inject_css, page_header

RECOMMENDATION_COLORS = {
    "Strong Buy": "#00C851",
    "Buy":        "#00d4a0",
    "Hold":       "#ffbb33",
    "Avoid":      "#ff4444",
}

ALL_CATEGORIES = ["All"] + list(POPULAR_FUNDS.keys())

RISK_ORDER = ["Low", "Low-Medium", "Medium", "Medium-High", "High", "Very High"]


# ── Caching ────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_all_funds(category: str | None) -> pd.DataFrame:
    return build_funds_dataframe(category)


@st.cache_data(ttl=3600, show_spinner=False)
def load_nav(scheme_code: int) -> pd.DataFrame | None:
    return get_nav_history(scheme_code)


@st.cache_data(ttl=3600, show_spinner=False)
def do_search(query: str) -> list[dict]:
    return search_funds(query)


# ── Chart builders ─────────────────────────────────────────────────────────────
def build_nav_chart(df: pd.DataFrame, fund_name: str, compare_dfs: list | None = None) -> go.Figure:
    """NAV chart — normalised to 100 so multiple funds are comparable."""
    fig = go.Figure()

    base_nav = float(df.iloc[0]["nav"])
    norm = df["nav"] / base_nav * 100

    fig.add_trace(go.Scatter(
        x=df["date"], y=norm,
        name=fund_name,
        line=dict(color="#00d4a0", width=2.5),
        hovertemplate="%{x|%b %Y}<br>Normalised: %{y:.1f}<extra></extra>",
    ))

    palette = ["#FF9800", "#2196F3", "#E040FB", "#FF5722"]
    if compare_dfs:
        for i, (cdf, cname) in enumerate(compare_dfs):
            if cdf is None or cdf.empty:
                continue
            cb = float(cdf.iloc[0]["nav"])
            cnorm = cdf["nav"] / cb * 100
            fig.add_trace(go.Scatter(
                x=cdf["date"], y=cnorm,
                name=cname,
                line=dict(color=palette[i % len(palette)], width=1.8, dash="dot"),
                hovertemplate="%{x|%b %Y}<br>%{y:.1f}<extra></extra>",
            ))

    fig.update_layout(
        template="plotly_dark", height=400,
        title=f"NAV Growth (Normalised to 100)",
        xaxis_title=None, yaxis_title="Normalised NAV",
        legend=dict(orientation="h", y=1.06),
        margin=dict(l=0, r=0, t=48, b=0),
        hovermode="x unified",
    )
    return fig


def build_returns_bar(df_funds: pd.DataFrame, period: str) -> go.Figure:
    """Horizontal bar chart of funds sorted by return for a given period."""
    # Map period labels to DataFrame column names
    col_map = {"1M": "1M %", "3M": "3M %", "6M": "6M %",
               "1Y": "1Y %", "3Y": "3Y CAGR %", "5Y": "5Y CAGR %"}
    col = col_map.get(period, f"{period} %")
    if col not in df_funds.columns:
        return go.Figure()
    data = df_funds[["Fund", "Category", col]].dropna().sort_values(col, ascending=True).tail(20)
    colors = ["#00C851" if v >= 0 else "#ff4444" for v in data[col]]

    fig = go.Figure(go.Bar(
        x=data[col], y=data["Fund"],
        orientation="h",
        marker_color=colors,
        text=[f"{v:+.1f}%" for v in data[col]],
        textposition="outside",
        customdata=data["Category"],
        hovertemplate="<b>%{y}</b><br>%{customdata}<br>Return: %{x:.2f}%<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_dark", height=max(350, len(data) * 28),
        title=f"Top Funds by {period} Return",
        xaxis_title=f"{period} Return (%)",
        margin=dict(l=0, r=80, t=44, b=0),
    )
    return fig


def build_risk_return_scatter(df_funds: pd.DataFrame) -> go.Figure:
    """Risk (volatility) vs Return scatter."""
    data = df_funds.dropna(subset=["Volatility", "1Y %"]).copy()
    if data.empty:
        return go.Figure()

    cat_colors = {
        "Large Cap": "#2196F3", "Mid Cap": "#FF9800", "Small Cap": "#ff4444",
        "Flexi Cap": "#00d4a0", "ELSS (Tax Saving)": "#E040FB",
        "Index Funds": "#4CAF50", "Sectoral / Thematic": "#FF5722",
        "Hybrid": "#9C27B0", "Debt": "#607D8B",
    }

    fig = go.Figure()
    for cat in data["Category"].unique():
        sub = data[data["Category"] == cat]
        fig.add_trace(go.Scatter(
            x=sub["Volatility"], y=sub["1Y %"],
            mode="markers+text",
            name=cat,
            marker=dict(size=12, color=cat_colors.get(cat, "#aaa"), opacity=0.85,
                        line=dict(width=1, color="rgba(255,255,255,0.2)")),
            text=sub["Fund"].str.split().str[:2].str.join(" "),
            textposition="top center",
            textfont=dict(size=9),
            hovertemplate="<b>%{text}</b><br>Volatility: %{x:.1f}%<br>1Y Return: %{y:.1f}%<extra></extra>",
        ))

    fig.update_layout(
        template="plotly_dark", height=440,
        title="Risk vs Return (1Y) — bubble = fund",
        xaxis_title="Annualised Volatility (%)",
        yaxis_title="1Y Return (%)",
        legend=dict(orientation="h", y=-0.18),
        margin=dict(l=0, r=0, t=44, b=80),
    )
    return fig


def build_category_heatmap(df_funds: pd.DataFrame) -> go.Figure:
    """Average returns heatmap: category × time period."""
    periods = ["1M %", "3M %", "6M %", "1Y %", "3Y CAGR %", "5Y CAGR %"]
    pivot = df_funds.groupby("Category")[periods].mean().round(1)
    pivot = pivot.rename(columns=lambda c: c.replace(" %", "").replace(" CAGR", " CAGR"))

    if pivot.empty:
        return go.Figure()

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale="RdYlGn",
        text=pivot.values,
        texttemplate="%{text:.1f}%",
        textfont=dict(size=11),
        colorbar=dict(title="Return %"),
        hoverongaps=False,
    ))
    fig.update_layout(
        template="plotly_dark", height=360,
        title="Average Returns by Category & Period",
        margin=dict(l=0, r=0, t=44, b=0),
    )
    return fig


# ── UI helpers ─────────────────────────────────────────────────────────────────
def rec_badge(rec: str) -> str:
    color = RECOMMENDATION_COLORS.get(rec, "#aaa")
    return (
        f'<span style="background:{color}22; border:1.5px solid {color}; '
        f'border-radius:6px; padding:3px 10px; color:{color}; '
        f'font-weight:700; font-size:0.78rem;">{rec}</span>'
    )


def score_bar(score: int) -> str:
    color = "#00C851" if score >= 70 else ("#ffbb33" if score >= 50 else "#ff4444")
    return (
        f'<div style="background:rgba(255,255,255,0.07); border-radius:4px; height:8px; overflow:hidden;">'
        f'<div style="width:{score}%; background:{color}; height:100%; border-radius:4px;"></div></div>'
        f'<div style="font-size:0.72rem; color:#888; margin-top:2px;">{score}/100</div>'
    )


def render_fund_card(row: pd.Series) -> None:
    color = RECOMMENDATION_COLORS.get(row["Recommendation"], "#aaa")
    r1y = row.get("1Y %")
    r3y = row.get("3Y CAGR %")
    nav = row.get("NAV (₹)", "—")
    score = int(row.get("Score", 0))

    st.markdown(
        f"""
        <div style="border:1.5px solid {color}33; border-left:3px solid {color};
                    border-radius:10px; padding:14px 18px; margin-bottom:10px;
                    background:{color}08;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div style="font-weight:700; font-size:1rem; color:#e8e8e8;">{row["Fund"]}</div>
                    <div style="font-size:0.78rem; color:#778; margin-top:2px;">
                        {row["Category"]} &nbsp;·&nbsp; Risk: {row["Risk"]}
                    </div>
                </div>
                <div style="text-align:right;">
                    <span style="background:{color}22; border:1.5px solid {color}; border-radius:6px;
                                 padding:4px 12px; color:{color}; font-weight:800; font-size:0.85rem;">
                        {row["Recommendation"]}
                    </span>
                    <div style="font-size:0.72rem; color:#888; margin-top:4px;">Score: {score}/100</div>
                </div>
            </div>
            <div style="display:flex; gap:24px; margin-top:10px; flex-wrap:wrap;">
                <div><div style="font-size:0.68rem; color:#556; text-transform:uppercase;">NAV</div>
                     <div style="font-weight:600; color:#d0d0d0;">{"₹{:,.2f}".format(nav) if isinstance(nav, (int, float)) else nav}</div></div>
                <div><div style="font-size:0.68rem; color:#556; text-transform:uppercase;">1Y Return</div>
                     <div style="font-weight:700; color:{"#00C851" if r1y and r1y>0 else "#ff4444"};">
                         {f"{r1y:+.1f}%" if r1y is not None else "—"}</div></div>
                <div><div style="font-size:0.68rem; color:#556; text-transform:uppercase;">3Y CAGR</div>
                     <div style="font-weight:700; color:{"#00C851" if r3y and r3y>0 else "#ff4444"};">
                         {f"{r3y:+.1f}%" if r3y is not None else "—"}</div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Main app ───────────────────────────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="MF Dashboard — India",
        page_icon="💹",
        layout="wide",
    )
    inject_css()
    page_header(
        "Indian Mutual Funds Dashboard",
        "NAV data via mfapi.in · Returns, risk metrics & recommendations"
    )

    # ── Sidebar ────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("Filters")

        selected_cat = st.selectbox("Category", ALL_CATEGORIES)
        cat_arg = None if selected_cat == "All" else selected_cat

        risk_filter = st.multiselect(
            "Risk Level",
            options=RISK_ORDER,
            default=RISK_ORDER,
            help="Filter funds by risk profile",
        )

        rec_filter = st.multiselect(
            "Recommendation",
            options=["Strong Buy", "Buy", "Hold", "Avoid"],
            default=["Strong Buy", "Buy", "Hold"],
        )

        sort_by = st.selectbox(
            "Sort table by",
            ["Score", "1Y %", "3Y CAGR %", "5Y CAGR %", "1M %", "Sharpe (1Y)"],
        )

        st.divider()

        # Fund search
        st.subheader("Search Fund")
        search_query = st.text_input("Name / keyword", placeholder="e.g. SBI Bluechip")
        search_btn = st.button("Search")

        st.divider()
        refresh = st.button("🔄 Refresh Data")
        if refresh:
            st.cache_data.clear()

        st.divider()
        st.caption("Data: mfapi.in (free, no key)")
        st.caption("Returns: point-to-point (1M–1Y) / CAGR (3Y, 5Y)")
        st.caption("⚠️ Not financial advice. Do your own research.")

    # ── Search results ─────────────────────────────────────────────────────────
    if search_btn and search_query.strip():
        st.subheader(f"Search results for: '{search_query}'")
        with st.spinner("Searching mfapi.in…"):
            results = do_search(search_query.strip())
        if results:
            res_df = pd.DataFrame(results[:30])
            st.dataframe(res_df, hide_index=True, use_container_width=True)
            st.caption("Copy the Scheme Code and use 'Explore Fund' below to load NAV data.")
        else:
            st.info("No results found.")
        st.divider()

    # ── Load funds data ────────────────────────────────────────────────────────
    with st.spinner("Loading mutual fund data from mfapi.in…"):
        df_all = load_all_funds(cat_arg)

    if df_all.empty:
        st.error("Could not fetch fund data. Check your internet connection.")
        st.stop()

    # Apply filters
    df = df_all.copy()
    if risk_filter:
        df = df[df["Risk"].isin(risk_filter)]
    if rec_filter:
        df = df[df["Recommendation"].isin(rec_filter)]

    df = df.sort_values(sort_by, ascending=False, na_position="last").reset_index(drop=True)

    # ── Summary KPIs ───────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Funds Loaded", len(df_all))
    k2.metric("Showing", len(df))
    best_1y = df.nlargest(1, "1Y %")
    if not best_1y.empty:
        k3.metric("Best 1Y Return", f"{best_1y.iloc[0]['1Y %']:+.1f}%",
                  delta=best_1y.iloc[0]["Fund"].split()[0])
    best_3y = df.nlargest(1, "3Y CAGR %")
    if not best_3y.empty:
        k4.metric("Best 3Y CAGR", f"{best_3y.iloc[0]['3Y CAGR %']:+.1f}%",
                  delta=best_3y.iloc[0]["Fund"].split()[0])
    top_score = df.nlargest(1, "Score")
    if not top_score.empty:
        k5.metric("Top Score", f"{int(top_score.iloc[0]['Score'])}/100",
                  delta=top_score.iloc[0]["Fund"].split()[0])

    st.divider()

    # ── Tabs ───────────────────────────────────────────────────────────────────
    tab_rec, tab_compare, tab_charts, tab_explore = st.tabs([
        "🏆 Recommendations", "📋 Compare Funds", "📊 Charts", "🔍 Explore Fund",
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1: Recommendations
    # ══════════════════════════════════════════════════════════════════════════
    with tab_rec:
        st.subheader("Top Picks")

        # Show strong buys first, then buys
        for rec_label in ["Strong Buy", "Buy", "Hold"]:
            subset = df[df["Recommendation"] == rec_label]
            if subset.empty:
                continue
            color = RECOMMENDATION_COLORS[rec_label]
            st.markdown(
                f'<h4 style="color:{color}; margin-bottom:4px;">{rec_label} ({len(subset)})</h4>',
                unsafe_allow_html=True,
            )
            # Show top 5 per recommendation level
            for _, row in subset.head(5).iterrows():
                render_fund_card(row)

        # Category-wise best pick
        st.divider()
        st.subheader("Best Pick per Category")
        cat_cols = st.columns(3)
        for i, cat in enumerate(POPULAR_FUNDS.keys()):
            sub = df_all[df_all["Category"] == cat].nlargest(1, "Score")
            if sub.empty:
                continue
            r = sub.iloc[0]
            color = RECOMMENDATION_COLORS.get(r["Recommendation"], "#aaa")
            with cat_cols[i % 3]:
                st.markdown(
                    f"""<div style="border:1px solid {color}44; border-radius:8px;
                                    padding:12px 14px; margin-bottom:8px;">
                        <div style="font-size:0.7rem; color:#556; text-transform:uppercase;">{cat}</div>
                        <div style="font-weight:700; color:#ddd; font-size:0.9rem; margin:3px 0;">{r["Fund"]}</div>
                        <div style="display:flex; gap:12px; flex-wrap:wrap;">
                            <span style="font-size:0.78rem; color:{"#00C851" if r.get("1Y %") and r["1Y %"]>0 else "#aaa"};">
                                1Y: {f"{r['1Y %']:+.1f}%" if r.get("1Y %") is not None else "—"}
                            </span>
                            <span style="background:{color}22; border:1px solid {color}; border-radius:4px;
                                         padding:1px 7px; font-size:0.72rem; color:{color}; font-weight:700;">
                                {r["Recommendation"]}
                            </span>
                        </div>
                    </div>""",
                    unsafe_allow_html=True,
                )

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2: Compare Funds (table)
    # ══════════════════════════════════════════════════════════════════════════
    with tab_compare:
        st.subheader("Fund Comparison Table")

        display_cols = [
            "Fund", "Category", "Risk", "NAV (₹)",
            "1M %", "3M %", "6M %", "1Y %", "3Y CAGR %", "5Y CAGR %",
            "Volatility", "Sharpe (1Y)", "Score", "Recommendation",
        ]
        display_df = df[display_cols].copy()

        # Colour-code returns with pandas Styler
        return_cols = ["1M %", "3M %", "6M %", "1Y %", "3Y CAGR %", "5Y CAGR %"]

        def colour_return(val):
            if pd.isna(val):
                return ""
            return f"color: {'#00C851' if val >= 0 else '#ff4444'}; font-weight: 600"

        def colour_rec(val):
            c = RECOMMENDATION_COLORS.get(val, "#aaa")
            return f"color: {c}; font-weight: 700"

        styled = (
            display_df.style
            .map(colour_return, subset=return_cols)
            .map(colour_rec, subset=["Recommendation"])
            .format({c: "{:+.1f}" for c in return_cols if c in display_df.columns},
                    na_rep="—")
            .format({"NAV (₹)": "₹{:.2f}", "Volatility": "{:.1f}%",
                     "Sharpe (1Y)": "{:.2f}", "Score": "{:.0f}"}, na_rep="—")
        )
        st.dataframe(styled, hide_index=True, use_container_width=True, height=520)

        # Download
        csv = df[display_cols].to_csv(index=False)
        st.download_button("⬇ Download CSV", data=csv, file_name="mutual_funds.csv", mime="text/csv")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3: Charts
    # ══════════════════════════════════════════════════════════════════════════
    with tab_charts:
        c1, c2 = st.columns(2)

        with c1:
            # Labels map directly to the column prefix used in build_returns_bar
            period_choice = st.selectbox("Return period for bar chart",
                                         ["1Y", "3M", "6M", "3Y", "5Y"], key="bar_period")
            bar_df = df_all.copy()
            if cat_arg:
                bar_df = bar_df[bar_df["Category"] == cat_arg]
            st.plotly_chart(build_returns_bar(bar_df, period_choice), use_container_width=True)

        with c2:
            st.plotly_chart(build_risk_return_scatter(df_all if cat_arg is None else df_all[df_all["Category"] == cat_arg]),
                            use_container_width=True)

        st.plotly_chart(build_category_heatmap(df_all), use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4: Explore single fund
    # ══════════════════════════════════════════════════════════════════════════
    with tab_explore:
        st.subheader("Explore a Fund")

        fund_options = {f"{r['Fund']} ({r['Category']})": r["scheme_code"]
                        for _, r in df_all.iterrows()}
        selected_fund_label = st.selectbox("Select fund", list(fund_options.keys()), key="explore_sel")
        selected_code = fund_options[selected_fund_label]

        # Custom scheme code override
        custom_code = st.number_input("Or enter scheme code manually (from search)", value=0, step=1)
        if custom_code > 0:
            selected_code = int(custom_code)

        # Compare with another fund
        compare_labels = ["None"] + list(fund_options.keys())
        compare_label = st.selectbox("Compare with", compare_labels, key="compare_sel")
        compare_code = fund_options.get(compare_label)

        with st.spinner("Loading NAV history…"):
            nav_df = load_nav(selected_code)
            cmp_df = load_nav(compare_code) if compare_code else None

        if nav_df is None or nav_df.empty:
            st.warning("No NAV data found for this scheme code.")
        else:
            fund_display_name = nav_df.attrs.get("scheme_name", selected_fund_label)
            cmp_display_name  = cmp_df.attrs.get("scheme_name", compare_label) if cmp_df is not None else None

            # NAV chart
            compare_list = [(cmp_df, cmp_display_name)] if cmp_df is not None else None
            st.plotly_chart(
                build_nav_chart(nav_df, fund_display_name, compare_list),
                use_container_width=True,
            )

            # Period selector to zoom the chart
            zoom = st.radio("Period", ["1Y", "3Y", "5Y", "All"], horizontal=True, index=0)
            from datetime import datetime
            cutoff_map = {"1Y": 365, "3Y": 365 * 3, "5Y": 365 * 5, "All": 99999}
            cutoff = pd.Timestamp.now() - pd.Timedelta(days=cutoff_map[zoom])
            zoomed = nav_df[nav_df["date"] >= cutoff]
            cmp_zoomed = cmp_df[cmp_df["date"] >= cutoff] if cmp_df is not None else None
            cmp_list_z = [(cmp_zoomed, cmp_display_name)] if cmp_zoomed is not None else None
            if not zoomed.empty:
                st.plotly_chart(
                    build_nav_chart(zoomed, f"{fund_display_name} ({zoom})", cmp_list_z),
                    use_container_width=True,
                )

            # Returns & metrics
            st.divider()
            ret = calculate_returns(nav_df)
            s   = score_fund(ret)
            rec = get_recommendation(s, "", ret)

            col_metrics = st.columns(7)
            for col, (label, key) in zip(col_metrics, [
                ("1M", "1M"), ("3M", "3M"), ("6M", "6M"), ("1Y", "1Y"),
                ("3Y CAGR", "3Y"), ("5Y CAGR", "5Y"), ("Curr. NAV", "current_nav"),
            ]):
                val = ret.get(key)
                if key == "current_nav":
                    col.metric(label, f"₹{val:,.2f}" if val else "—")
                else:
                    col.metric(label, f"{val:+.1f}%" if val is not None else "—")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Score", f"{s}/100")
            m2.metric("Recommendation", rec)
            m3.metric("Volatility (1Y)", f"{ret.get('std_dev_1y', 0) or 0:.1f}%")
            m4.metric("Sharpe (1Y)", f"{ret.get('sharpe_1y') or 0:.2f}")

            # Raw NAV table
            with st.expander("View NAV data"):
                display = nav_df[["date", "nav"]].copy()
                display["date"] = display["date"].dt.strftime("%d %b %Y")
                st.dataframe(display.tail(60).iloc[::-1], hide_index=True, use_container_width=True)

            # Fund meta
            st.caption(
                f"Scheme: {nav_df.attrs.get('scheme_name', '—')} · "
                f"Fund House: {nav_df.attrs.get('fund_house', '—')} · "
                f"Type: {nav_df.attrs.get('scheme_type', '—')}"
            )


if __name__ == "__main__":
    main()
