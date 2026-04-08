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
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        /* ── Root & background ───────────────────────────────── */
        html, body, .stApp {
            font-family: 'Inter', sans-serif !important;
        }
        .stApp {
            background: linear-gradient(160deg, #080b10 0%, #0a0f0d 60%, #080b10 100%);
        }

        /* ── Hide Streamlit chrome ───────────────────────────── */
        #MainMenu, footer { visibility: hidden; }
        [data-testid="stHeader"] { background: transparent; }

        /* ── Sidebar ─────────────────────────────────────────── */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0d1117 0%, #090d0b 100%);
            border-right: 1px solid rgba(0,212,160,0.18);
        }

        /* ── Metric cards ────────────────────────────────────── */
        div[data-testid="metric-container"] {
            background: rgba(255,255,255,0.035);
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 12px;
            padding: 18px 20px 14px;
            transition: border-color 0.2s, background 0.2s;
        }
        div[data-testid="metric-container"]:hover {
            border-color: rgba(0,212,160,0.35);
            background: rgba(0,212,160,0.05);
        }
        div[data-testid="stMetricLabel"] > div {
            color: #7a8a88 !important;
            font-size: 0.7rem !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 0.6px;
        }
        div[data-testid="stMetricValue"] > div {
            color: #f0f0f0 !important;
            font-size: 1.45rem !important;
            font-weight: 700 !important;
        }
        div[data-testid="stMetricDelta"] > div {
            font-size: 0.8rem !important;
            font-weight: 500 !important;
        }

        /* ── Buttons ─────────────────────────────────────────── */
        .stButton > button {
            background: linear-gradient(135deg, #00d4a0 0%, #00a87f 100%) !important;
            color: #060b09 !important;
            font-weight: 700 !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 8px 20px !important;
            font-family: 'Inter', sans-serif !important;
            letter-spacing: 0.3px;
            transition: box-shadow 0.2s, transform 0.15s !important;
        }
        .stButton > button:hover {
            box-shadow: 0 0 18px rgba(0,212,160,0.45) !important;
            transform: translateY(-1px) !important;
        }
        .stButton > button:active { transform: translateY(0) !important; }

        /* ── Tabs ────────────────────────────────────────────── */
        .stTabs [data-baseweb="tab-list"] {
            background: rgba(255,255,255,0.03);
            border-radius: 10px;
            padding: 4px;
            gap: 4px;
            border: 1px solid rgba(255,255,255,0.06);
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 7px;
            color: #778;
            font-weight: 500;
            border: none !important;
            transition: all 0.15s;
        }
        .stTabs [data-baseweb="tab"]:hover {
            color: #ccc;
            background: rgba(255,255,255,0.05) !important;
        }
        .stTabs [aria-selected="true"] {
            background: rgba(0,212,160,0.12) !important;
            color: #00d4a0 !important;
        }
        .stTabs [data-baseweb="tab-highlight"] {
            background: #00d4a0 !important;
            height: 2px !important;
        }

        /* ── Expanders ───────────────────────────────────────── */
        div[data-testid="stExpander"] {
            border: 1px solid rgba(255,255,255,0.07) !important;
            border-radius: 10px !important;
            overflow: hidden;
        }
        div[data-testid="stExpander"] summary {
            background: rgba(255,255,255,0.025) !important;
            padding: 10px 16px !important;
            font-weight: 500 !important;
        }
        div[data-testid="stExpander"] summary:hover {
            background: rgba(0,212,160,0.06) !important;
        }

        /* ── Dividers ────────────────────────────────────────── */
        hr {
            border: none !important;
            border-top: 1px solid rgba(0,212,160,0.14) !important;
            margin: 20px 0 !important;
        }

        /* ── Headings ────────────────────────────────────────── */
        h1 {
            font-family: 'Inter', sans-serif !important;
            font-weight: 800 !important;
            letter-spacing: -0.5px !important;
            color: #f5f5f5 !important;
        }
        h2 {
            font-family: 'Inter', sans-serif !important;
            font-weight: 700 !important;
            color: #e0e0e0 !important;
        }
        h3 {
            font-family: 'Inter', sans-serif !important;
            font-weight: 600 !important;
            color: #00d4a0 !important;
        }

        /* ── Inputs & selects ────────────────────────────────── */
        [data-testid="stSelectbox"] > div > div {
            background: rgba(255,255,255,0.04) !important;
            border-color: rgba(255,255,255,0.1) !important;
            border-radius: 8px !important;
        }
        [data-testid="stTextInput"] input {
            background: rgba(255,255,255,0.04) !important;
            border-color: rgba(255,255,255,0.1) !important;
            border-radius: 8px !important;
            color: #e0e0e0 !important;
        }

        /* ── Slider ──────────────────────────────────────────── */
        [data-testid="stSlider"] [role="slider"] {
            background: #00d4a0 !important;
            border-color: #00d4a0 !important;
        }

        /* ── Alerts ──────────────────────────────────────────── */
        [data-testid="stAlert"] { border-radius: 10px !important; }

        /* ── Captions ────────────────────────────────────────── */
        [data-testid="stCaptionContainer"] { color: #556 !important; }

        /* ── Mobile / responsive ─────────────────────────────── */
        @media (max-width: 768px) {
            /* Always show Plotly toolbar on touch screens */
            .modebar { opacity: 1 !important; }
            /* Larger touch targets for modebar buttons */
            .modebar-btn { padding: 8px 10px !important; }
            /* Stack metric columns on narrow screens */
            [data-testid="stHorizontalBlock"] {
                flex-wrap: wrap !important;
            }
            [data-testid="stHorizontalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] {
                min-width: 45% !important;
                flex: 1 1 45% !important;
            }
            /* Reduce padding on mobile */
            .main .block-container {
                padding-left: 0.75rem !important;
                padding-right: 0.75rem !important;
            }
        }

        /* ── Signal badge pulse animations ───────────────────── */
        @keyframes pulse-buy {
            0%, 100% { box-shadow: 0 0 8px rgba(0,200,81,0.3); }
            50%       { box-shadow: 0 0 22px rgba(0,200,81,0.7), 0 0 40px rgba(0,200,81,0.2); }
        }
        @keyframes pulse-sell {
            0%, 100% { box-shadow: 0 0 8px rgba(255,68,68,0.3); }
            50%       { box-shadow: 0 0 22px rgba(255,68,68,0.7), 0 0 40px rgba(255,68,68,0.2); }
        }
        @keyframes pulse-hold {
            0%, 100% { box-shadow: 0 0 8px rgba(255,187,51,0.25); }
            50%       { box-shadow: 0 0 18px rgba(255,187,51,0.55), 0 0 32px rgba(255,187,51,0.15); }
        }
        .sig-badge-buy  { animation: pulse-buy  2.2s ease-in-out infinite; }
        .sig-badge-sell { animation: pulse-sell 2.2s ease-in-out infinite; }
        .sig-badge-hold { animation: pulse-hold 2.2s ease-in-out infinite; }
        </style>
        """,
        unsafe_allow_html=True,
    )


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
        f'<p style="color:#556;font-size:0.85rem;margin:4px 0 0;font-weight:400;">{subtitle}</p>'
        if subtitle else ""
    )
    st.markdown(
        f"""
        <div style="
            border-left: 3px solid #00d4a0;
            padding: 10px 0 10px 16px;
            margin-bottom: 8px;
        ">
            <h1 style="margin:0;font-size:1.6rem;">{title}</h1>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
