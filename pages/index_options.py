"""
Redirect stub — navigation is now handled inside dashboard.py (single-page app).
If someone navigates directly to /index_options, switch to dashboard with options active.
"""
import sys
sys.path.insert(0, ".")
import streamlit as st

st.session_state["_nav_page"] = "options"
st.switch_page("dashboard.py")
