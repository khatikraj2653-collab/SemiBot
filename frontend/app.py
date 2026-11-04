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

# Full-screen loader shown IMMEDIATELY so users don't see a blank page while
# the heavy imports and landing HTML render on first visit.
# Cleared at the end of the script.
_loading_placeholder = st.empty()
_loading_placeholder.markdown(
    """
    <div style="position:fixed;inset:0;display:flex;align-items:center;justify-content:center;
                background:#171B21;z-index:999999;flex-direction:column;gap:14px;">
      <div style="width:44px;height:44px;border:3px solid rgba(91,155,255,.2);
                  border-top-color:#5B9BFF;border-radius:50%;
                  animation:sb-ld 0.9s linear infinite;"></div>
      <div style="color:#C7D1DF;font-family:Inter,sans-serif;font-size:14px;">
        Loading SemiBot…
      </div>
      <style>@keyframes sb-ld{to{transform:rotate(360deg)}}</style>
    </div>
    """,
    unsafe_allow_html=True,
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

# ---- Live ticker prices for the coverage strip ----
# Fetched once per 2 minutes (cached) so the landing page shows real
# prices with scrolling animation instead of a static list.
import yfinance as yf

TICKER_SYMBOLS = [
    "NVDA", "TSM", "ASML", "MU", "AMD", "AVGO", "INTC", "QCOM",
    "ARM", "AMAT", "LRCX", "KLAC", "005930.KS", "000660.KS", "8035.T", "IFX.DE",
]

@st.cache_data(ttl=120, show_spinner=False)
def fetch_ticker_prices():
    out = []
    try:
        data = yf.download(
            " ".join(TICKER_SYMBOLS),
            period="2d",
            interval="1d",
            progress=False,
            group_by="ticker",
            auto_adjust=False,
            threads=True,
        )
    except Exception:
        return [{"symbol": s, "price": None, "change": None} for s in TICKER_SYMBOLS]
    for s in TICKER_SYMBOLS:
        try:
            closes = data[s]["Close"].dropna()
            if len(closes) >= 2:
                price = float(closes.iloc[-1])
                prev = float(closes.iloc[-2])
                change = (price - prev) / prev * 100 if prev else 0.0
                out.append({"symbol": s, "price": price, "change": change})
            elif len(closes) == 1:
                out.append({"symbol": s, "price": float(closes.iloc[-1]), "change": 0.0})
            else:
                out.append({"symbol": s, "price": None, "change": None})
        except Exception:
            out.append({"symbol": s, "price": None, "change": None})
    return out

def build_ticker_strip_html(rows):
    def fmt(r):
        if r["price"] is None:
            return f'<span class="t-item"><b>{r["symbol"]}</b></span>'
        price_str = f"{r['price']:.2f}"
        chg = r["change"] or 0.0
        sign = "+" if chg >= 0 else ""
        color_class = "t-up" if chg >= 0 else "t-dn"
        return (
            f'<span class="t-item"><b>{r["symbol"]}</b> '
            f'<span class="t-px">{price_str}</span> '
            f'<span class="{color_class}">{sign}{chg:.2f}%</span></span>'
        )
    items = "".join(fmt(r) for r in rows)
    # Duplicate once so the CSS animation loops seamlessly
    inner = items + items
    return f'<div class="strip-tickers scrolling"><div class="strip-move">{inner}</div></div>'

ticker_rows = fetch_ticker_prices()
live_ticker_html = build_ticker_strip_html(ticker_rows)

# Load landing.html from project root
landing_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'landing.html')
with open(landing_path, 'r', encoding='utf-8') as f:
    html_content = f.read()

# Replace the static ticker strip with the live scrolling one
import re
html_content = re.sub(
    r'<div class="strip-tickers">.*?</div>',
    live_ticker_html,
    html_content,
    count=1,
    flags=re.DOTALL,
)

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

/* Scrolling live ticker tape */
.strip-tickers.scrolling {
    overflow: hidden !important;
    text-overflow: unset !important;
    position: relative;
    flex: 1;
    min-width: 0;
}
.strip-tickers.scrolling .strip-move {
    display: inline-block;
    white-space: nowrap;
    animation: strip-scroll 60s linear infinite;
    will-change: transform;
}
.strip-tickers.scrolling:hover .strip-move { animation-play-state: paused; }
.strip-tickers .t-item { margin-right: 28px; font-family: var(--mono, monospace); font-size: 12.5px; }
.strip-tickers .t-item b { color: #E8ECF1; font-weight: 600; margin-right: 6px; }
.strip-tickers .t-px { color: #C7D1DF; margin-right: 6px; }
.strip-tickers .t-up { color: #34D399; font-weight: 600; }
.strip-tickers .t-dn { color: #F87171; font-weight: 600; }
@keyframes strip-scroll {
    from { transform: translateX(0); }
    to   { transform: translateX(-50%); }
}

/* Ensure body background matches original exactly */
body {
    background-color: #1D222A !important;
}
</style>
"""
html_content = html_content.replace('<head>', '<head>' + iframe_fixes)

# Render landing page
st.components.v1.html(html_content, height=7400, scrolling=True)

render_chat_bubble()

# Clear the full-screen loader now that the landing page has rendered.
_loading_placeholder.empty()