"""
Redirect stub — navigation is now handled inside dashboard.py (single-page app).
If someone navigates directly to /about, switch to dashboard with about active.
"""
import sys
sys.path.insert(0, ".")
import streamlit as st

st.session_state["_nav_page"] = "about"
st.switch_page("dashboard.py")
