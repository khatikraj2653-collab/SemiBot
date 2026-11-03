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

# SEO tags injected into the real top-level document (st.markdown runs in
# Streamlit's own DOM, unlike st.components.v1.html which sandboxes into an
# iframe Google's crawler won't associate with this page's <head>).
st.markdown("""
<script>
(function() {
  document.title = "SemiBot — AI Semiconductor Equity Analyser";
  function setMeta(attr, key, content) {
    let el = document.querySelector(`meta[${attr}="${key}"]`);
    if (!el) { el = document.createElement('meta'); el.setAttribute(attr, key); document.head.appendChild(el); }
    el.setAttribute('content', content);
  }
  const desc = "18-factor agentic RAG system for semiconductor equity analysis — real-time causal-chain prediction, built by Raj Tejpal Khatik.";
  setMeta('name', 'description', desc);
  setMeta('property', 'og:title', "SemiBot — AI Semiconductor Equity Analyser");
  setMeta('property', 'og:description', desc);
  setMeta('property', 'og:type', 'website');
  setMeta('property', 'og:url', 'https://semibot-raj.streamlit.app/');
  setMeta('name', 'twitter:card', 'summary_large_image');
  setMeta('name', 'twitter:title', "SemiBot — AI Semiconductor Equity Analyser");
  setMeta('name', 'twitter:description', desc);

  let canonical = document.querySelector('link[rel="canonical"]');
  if (!canonical) { canonical = document.createElement('link'); canonical.setAttribute('rel', 'canonical'); document.head.appendChild(canonical); }
  canonical.setAttribute('href', 'https://semibot-raj.streamlit.app/');

  if (!document.getElementById('semibot-jsonld')) {
    const s = document.createElement('script');
    s.type = 'application/ld+json';
    s.id = 'semibot-jsonld';
    s.textContent = JSON.stringify({
      "@context": "https://schema.org",
      "@type": "SoftwareApplication",
      "name": "SemiBot",
      "applicationCategory": "FinanceApplication",
      "operatingSystem": "Web",
      "url": "https://semibot-raj.streamlit.app/",
      "description": desc,
      "author": {
        "@type": "Person",
        "name": "Raj Tejpal Khatik",
        "sameAs": [
          "https://www.linkedin.com/in/raj-khatik-6ab086395",
          "https://github.com/khatikraj2653-collab",
          "https://portfolio-raj.pages.dev/"
        ]
      }
    });
    document.head.appendChild(s);
  }
})();
</script>
""", unsafe_allow_html=True)

# Google Analytics (GA4)
st.markdown("""
<script async src="https://www.googletagmanager.com/gtag/js?id=G-LNXBSERGCX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-LNXBSERGCX');
</script>
""", unsafe_allow_html=True)

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
    background: repeating-linear-gradient(90deg,rgba(255,255,255,.022) 0 1px,transparent 1px 4px), linear-gradient(180deg,#232932,#171B21) !important;
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
    background: #5B9BFF !important;
    color: #06101F !important;
    border: none !important;
    border-radius: 9px !important;
    padding: 9px 20px !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
    text-decoration: none !important;
    display: inline-block !important;
}
[data-testid="stPageLink"] a:hover {
    background: #8BB8FF !important;
    transform: translateY(-1px) !important;
}
[data-testid="stPageLink"] a p { color: #06101F !important; }
[data-testid="stPageLink"] a { background: linear-gradient(180deg,#A6CDFF 0%,#5B9BFF 46%,#2F6BD1 54%,#4E8AE6 100%) !important; border: 1px solid #1A4590 !important; text-shadow: 0 1px 0 rgba(255,255,255,.45) !important; box-shadow: inset 0 1px 0 rgba(255,255,255,.65), inset 0 -2px 3px rgba(10,40,100,.35), 0 3px 7px rgba(0,0,0,.55) !important; }
[data-testid="stPageLink"] a:hover { filter: brightness(1.09); transform: none !important; }
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
    background-color: #1D222A !important;
}
</style>
"""
html_content = html_content.replace('<head>', '<head>' + iframe_fixes)

# Render landing page
st.components.v1.html(html_content, height=5600, scrolling=True)

render_chat_bubble()