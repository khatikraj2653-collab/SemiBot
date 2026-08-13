import streamlit as st
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from log_client import log_event
from chat_bubble import render_chat_bubble

st.set_page_config(
    page_title="SemiBot - AI Semiconductor Equity Analyser",
    page_icon="::",
    layout="wide",
    initial_sidebar_state="collapsed"
)

if "visit_logged" not in st.session_state:
    log_event("visit", detail="landing page")
    st.session_state.visit_logged = True

# Hide ALL Streamlit chrome including sidebar and page nav
st.markdown("""
<style>
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
[data-testid="stDecoration"] { display: none; }
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
[data-testid="stSidebarNav"] { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
[data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: #04080F !important;
}

/* Style the Get Started page link to match landing page nav button */
[data-testid="stPageLink"] {
    position: fixed !important;
    top: 14px !important;
    right: 48px !important;
    z-index: 99999 !important;
    width: auto !important;
}
[data-testid="stPageLink"] a {
    background: linear-gradient(135deg, #0055FF, #00AAFF) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 9px !important;
    padding: 9px 22px !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
    box-shadow: 0 0 18px rgba(0,140,255,0.4) !important;
    text-decoration: none !important;
    display: inline-block !important;
}
[data-testid="stPageLink"] a:hover {
    box-shadow: 0 0 30px rgba(0,180,255,0.6) !important;
    transform: translateY(-1px) !important;
}
[data-testid="stPageLink"] svg { display: none !important; }

/* Force Streamlit iframe to have no background interference */
iframe[title="streamlit_component"] {
    background: transparent !important;
}
</style>
""", unsafe_allow_html=True)

# Native navigation button - fixed position, styled as nav CTA
st.page_link("pages/analysis.py", label="Get Started →")

# Load landing.html from project root
landing_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'landing.html')
with open(landing_path, 'r', encoding='utf-8') as f:
    html_content = f.read()

# Make goApp click the real Streamlit Get Started link
html_content = html_content.replace(
    "function goApp(){window.location.href='https://semibot-raj.streamlit.app';}",
    "function goApp(){try{window.parent.document.querySelector('[data-testid=\"stPageLink\"] a').click();}catch(e){}}"
)

# CSS overrides for iframe rendering
iframe_fixes = """
<style>
/* Fix nav positioning inside iframe */
.nav {
    position: absolute !important;
    justify-content: center !important;
    gap: 40px !important;
}
.nav-logo {
    position: absolute !important;
    left: 48px !important;
}
.nav-links {
    position: static !important;
}

/* Hero 100vh doesn't work in iframe */
#hero {
    min-height: auto !important;
}

/* Disable welcome modal */
#welcomeModal {
    display: none !important;
}

/* Hide the nav Get Started button (replaced by Streamlit page_link above) */
.nav-cta {
    display: none !important;
}

/* Ensure body background matches original exactly */
body {
    background: #04080F !important;
}
</style>
"""
html_content = html_content.replace('<head>', '<head>' + iframe_fixes)

# Render landing page
st.components.v1.html(html_content, height=3650, scrolling=True)

render_chat_bubble()