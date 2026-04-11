"""
Shared visual theme for all Streamlit dashboards.
Call inject_css() once at the top of main() in each app, right after set_page_config.
"""
import streamlit as st

TEAL = "#00d4a0"

SIGNAL_COLORS = {
    "BUY":  "#00C851",
    "SELL": "#ff4444",
    "HOLD": "#ffbb33",
}


def inject_css() -> None:
    """Inject global CSS + Google Fonts into the Streamlit app."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,300;0,14..32,400;0,14..32,500;0,14..32,600;0,14..32,700;0,14..32,800&display=swap');

        /* ── Root ────────────────────────────────────────────── */
        html, body, .stApp {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
            -webkit-font-smoothing: antialiased;
        }
        .stApp {
            background: #080c0b;
        }

        /* ── Hide Streamlit chrome ───────────────────────────── */
        #MainMenu, footer { visibility: hidden; }
        [data-testid="stHeader"] { background: transparent; }

        /* ── Main content area ───────────────────────────────── */
        .main .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;
        }

        /* ── Sidebar ─────────────────────────────────────────── */
        section[data-testid="stSidebar"] {
            background: #0a0e0d;
            border-right: 1px solid rgba(255,255,255,0.06);
        }
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
            color: rgba(255,255,255,0.9) !important;
            font-size: 0.8rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.08em !important;
            text-transform: uppercase !important;
        }

        /* ── Metric cards ────────────────────────────────────── */
        div[data-testid="metric-container"] {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 16px;
            padding: 16px 18px 13px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.25), 0 1px 2px rgba(0,0,0,0.15);
            transition: border-color 0.25s ease, background 0.25s ease, box-shadow 0.25s ease;
        }
        div[data-testid="metric-container"]:hover {
            border-color: rgba(0,212,160,0.28);
            background: rgba(0,212,160,0.04);
            box-shadow: 0 4px 16px rgba(0,0,0,0.3), 0 0 0 1px rgba(0,212,160,0.1);
        }
        div[data-testid="stMetricLabel"] > div {
            color: rgba(255,255,255,0.38) !important;
            font-size: 0.68rem !important;
            font-weight: 500 !important;
            text-transform: uppercase;
            letter-spacing: 0.07em;
        }
        div[data-testid="stMetricValue"] > div {
            color: rgba(255,255,255,0.92) !important;
            font-size: 1.35rem !important;
            font-weight: 600 !important;
            letter-spacing: -0.02em;
        }
        div[data-testid="stMetricDelta"] > div {
            font-size: 0.75rem !important;
            font-weight: 500 !important;
        }

        /* ── Refresh button ──────────────────────────────────── */
        .stButton > button {
            background: rgba(0,212,160,0.1) !important;
            color: #00d4a0 !important;
            font-weight: 600 !important;
            border: 1px solid rgba(0,212,160,0.3) !important;
            border-radius: 10px !important;
            padding: 8px 20px !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 0.85rem !important;
            letter-spacing: 0.01em;
            transition: all 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94) !important;
        }
        .stButton > button:hover {
            background: rgba(0,212,160,0.18) !important;
            border-color: rgba(0,212,160,0.55) !important;
            box-shadow: 0 4px 14px rgba(0,212,160,0.15) !important;
            transform: translateY(-1px) !important;
        }
        .stButton > button:active {
            transform: translateY(0) !important;
            box-shadow: none !important;
        }

        /* ── Tabs ────────────────────────────────────────────── */
        .stTabs [data-baseweb="tab-list"] {
            background: rgba(255,255,255,0.025);
            border-radius: 12px;
            padding: 4px 5px;
            gap: 2px;
            border: 1px solid rgba(255,255,255,0.055);
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            color: rgba(255,255,255,0.38);
            font-weight: 500;
            font-size: 0.875rem;
            border: none !important;
            padding: 7px 18px !important;
            transition: all 0.18s ease;
            letter-spacing: 0.01em;
        }
        .stTabs [data-baseweb="tab"]:hover {
            color: rgba(255,255,255,0.72);
            background: rgba(255,255,255,0.05) !important;
        }
        .stTabs [aria-selected="true"] {
            background: rgba(0,212,160,0.1) !important;
            color: #00d4a0 !important;
            box-shadow: 0 1px 4px rgba(0,0,0,0.2) !important;
        }
        .stTabs [data-baseweb="tab-highlight"] {
            display: none !important;
        }
        .stTabs [data-baseweb="tab-border"] {
            display: none !important;
        }

        /* ── Expanders ───────────────────────────────────────── */
        div[data-testid="stExpander"] {
            border: 1px solid rgba(255,255,255,0.07) !important;
            border-radius: 14px !important;
            overflow: hidden;
            background: rgba(255,255,255,0.02) !important;
        }
        div[data-testid="stExpander"] summary {
            background: transparent !important;
            padding: 12px 18px !important;
            font-weight: 500 !important;
            color: rgba(255,255,255,0.6) !important;
            font-size: 0.88rem !important;
        }
        div[data-testid="stExpander"] summary:hover {
            color: rgba(255,255,255,0.85) !important;
        }

        /* ── Dividers ────────────────────────────────────────── */
        hr {
            border: none !important;
            border-top: 1px solid rgba(255,255,255,0.07) !important;
            margin: 22px 0 !important;
        }

        /* ── Headings ────────────────────────────────────────── */
        h1 {
            font-family: 'Inter', sans-serif !important;
            font-weight: 700 !important;
            letter-spacing: -0.03em !important;
            color: rgba(255,255,255,0.94) !important;
        }
        h2 {
            font-family: 'Inter', sans-serif !important;
            font-weight: 600 !important;
            letter-spacing: -0.02em !important;
            color: rgba(255,255,255,0.82) !important;
        }
        h3 {
            font-family: 'Inter', sans-serif !important;
            font-weight: 600 !important;
            letter-spacing: -0.01em !important;
            color: rgba(255,255,255,0.75) !important;
        }

        /* ── Inputs & selects ────────────────────────────────── */
        [data-testid="stSelectbox"] > div > div {
            background: rgba(255,255,255,0.04) !important;
            border: 1px solid rgba(255,255,255,0.09) !important;
            border-radius: 10px !important;
            transition: border-color 0.2s ease !important;
        }
        [data-testid="stSelectbox"] > div > div:focus-within {
            border-color: rgba(0,212,160,0.45) !important;
        }
        [data-testid="stTextInput"] input {
            background: rgba(255,255,255,0.04) !important;
            border: 1px solid rgba(255,255,255,0.09) !important;
            border-radius: 10px !important;
            color: rgba(255,255,255,0.88) !important;
        }

        /* ── Alerts ──────────────────────────────────────────── */
        [data-testid="stAlert"] {
            border-radius: 12px !important;
            border-width: 1px !important;
        }

        /* ── Captions ────────────────────────────────────────── */
        [data-testid="stCaptionContainer"] {
            color: rgba(255,255,255,0.28) !important;
            font-size: 0.75rem !important;
        }

        /* ── Dataframes ──────────────────────────────────────── */
        [data-testid="stDataFrame"] {
            border-radius: 12px !important;
            overflow: hidden;
        }

        /* ── Mobile ──────────────────────────────────────────── */
        @media (max-width: 768px) {
            .modebar { opacity: 1 !important; }
            .modebar-btn { padding: 8px 10px !important; }
            [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
            [data-testid="stHorizontalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] {
                min-width: 45% !important;
                flex: 1 1 45% !important;
            }
            .main .block-container {
                padding-left: 0.75rem !important;
                padding-right: 0.75rem !important;
            }
        }

        /* ── Signal badge animations ─────────────────────────── */
        @keyframes pulse-buy {
            0%, 100% { box-shadow: 0 0 0 0 rgba(0,200,81,0); }
            50%       { box-shadow: 0 0 20px 2px rgba(0,200,81,0.18); }
        }
        @keyframes pulse-sell {
            0%, 100% { box-shadow: 0 0 0 0 rgba(255,68,68,0); }
            50%       { box-shadow: 0 0 20px 2px rgba(255,68,68,0.18); }
        }
        @keyframes pulse-hold {
            0%, 100% { box-shadow: 0 0 0 0 rgba(255,187,51,0); }
            50%       { box-shadow: 0 0 16px 2px rgba(255,187,51,0.15); }
        }
        .sig-badge-buy  { animation: pulse-buy  3s ease-in-out infinite; }
        .sig-badge-sell { animation: pulse-sell 3s ease-in-out infinite; }
        .sig-badge-hold { animation: pulse-hold 3s ease-in-out infinite; }
        </style>
        """,
        unsafe_allow_html=True,
    )


_NAV_CSS = """
<style>
.app-nav {
    display: flex;
    flex-direction: row;
    gap: 10px;
    margin-bottom: 16px;
    align-items: center;
}
.app-nav a {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 138px;
    padding: 10px 22px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    text-decoration: none !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    font-weight: 500;
    font-size: 0.875rem;
    color: rgba(255,255,255,0.42) !important;
    letter-spacing: 0.01em;
    transition: all 0.22s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    box-shadow: 0 1px 3px rgba(0,0,0,0.2);
    white-space: nowrap;
    cursor: pointer;
}
.app-nav a:hover {
    background: rgba(255,255,255,0.07) !important;
    border-color: rgba(255,255,255,0.15) !important;
    color: rgba(255,255,255,0.75) !important;
    transform: translateY(-1px);
    box-shadow: 0 5px 14px rgba(0,0,0,0.28);
    text-decoration: none !important;
}
.app-nav a.nav-active {
    background: rgba(0,212,160,0.09) !important;
    border-color: rgba(0,212,160,0.4) !important;
    color: #00d4a0 !important;
    box-shadow: 0 4px 16px rgba(0,212,160,0.12), 0 1px 3px rgba(0,0,0,0.2) !important;
    pointer-events: none;
    cursor: default;
}
</style>
"""


def render_nav(active: str) -> None:
    """Render the top navigation bar as three HTML anchor boxes.

    active: one of 'equities', 'options', 'about'
    """
    def _cls(key: str) -> str:
        return 'nav-active' if active == key else ''

    html = (
        _NAV_CSS
        + f"""
<nav class="app-nav">
  <a href="/" class="{_cls('equities')}">📈 Equities</a>
  <a href="/index_options" class="{_cls('options')}">🎯 Index Options</a>
  <a href="/about" class="{_cls('about')}">ℹ️ About</a>
</nav>
"""
    )
    st.markdown(html, unsafe_allow_html=True)


def signal_badge(signal: str, confidence: int, subtitle: str = "") -> str:
    """Return an animated glassmorphism signal badge as an HTML string."""
    color = SIGNAL_COLORS.get(signal, "#aaa")
    cls = f"sig-badge-{signal.lower()}"
    sub = (
        f'<div style="color:{color};opacity:0.75;font-size:0.82rem;margin-top:4px;">{subtitle}</div>'
        if subtitle else ""
    )
    return f"""
    <div class="{cls}" style="
        background:{color}16;
        border:2px solid {color};
        border-radius:14px;
        padding:18px 28px;
        text-align:center;
        backdrop-filter:blur(8px);
    ">
        <div style="font-size:2.4rem;font-weight:800;color:{color};letter-spacing:1px;">{signal}</div>
        <div style="color:{color};opacity:0.8;font-size:0.9rem;margin-top:3px;">Confidence: {confidence}%</div>
        {sub}
    </div>
    """


def page_header(title: str, subtitle: str = "") -> None:
    """Render a styled page header with optional subtitle."""
    sub_html = (
        f'<p style="color:rgba(255,255,255,0.35);font-size:0.82rem;margin:5px 0 0;'
        f'font-weight:400;letter-spacing:0.01em;">{subtitle}</p>'
        if subtitle else ""
    )
    st.markdown(
        f"""
        <div style="padding: 4px 0 12px 0; margin-bottom: 4px;">
            <h1 style="margin:0;font-size:1.55rem;font-weight:700;
                       color:rgba(255,255,255,0.93);letter-spacing:-0.03em;">{title}</h1>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
