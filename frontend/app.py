import sys
import os
import re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from graph.workflow import app

load_dotenv()
import base64
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'robot_b64.txt'), 'r') as f:
    ROBOT_IMG = f.read()

st.set_page_config(
    page_title="SemiBot",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@500;600;700;800&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: #1E1E1E !important;
    font-family: 'Inter', sans-serif !important;
            .stSpinner > div { color: #FFFFFF !important; }
[data-testid="stStatusWidget"] { color: #FFFFFF !important; }
}
           
            
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    background-image:
        linear-gradient(rgba(0,140,255,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,140,255,0.03) 1px, transparent 1px);
    background-size: 44px 44px;
    pointer-events: none; z-index: 0;
}
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
[data-testid="stDecoration"] { display: none; }
.block-container { padding: 0 !important; max-width: 100% !important; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: #1E1E1E !important;
    border-right: 1px solid #569CD6 !important;
    display: block !important;
    visibility: visible !important;
    min-width: 240px !important;
    max-width: 240px !important;
    transform: none !important;
}
[data-testid="collapsedControl"] { display: none !important; }
[data-testid="stSidebar"] * { color: #FFFFFF !important; }
[data-testid="stSidebarContent"] { padding: 20px 16px !important; }

/* Buttons */
.stButton > button {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
    transition: all 0.2s !important;
    border: none !important;
    background: linear-gradient(135deg, #0055FF, #00AAFF) !important;
    color: #fff !important;
}
.stButton > button:hover { opacity: 0.9 !important; transform: translateY(-1px) !important; }

/* Input */
.stTextInput input {
    background: rgba(15,50,120,0.9) !important;
    border: 1px solid rgba(0,140,255,0.22) !important;
    border-radius: 14px !important;
    padding: 16px 20px !important;
    color: #E8F4FF !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 1rem !important;
    .stTextInput input::placeholder { color: #C8E8FF !important; }
    .stTextInput input { caret-color: #00AAFF !important; }
}
.stTextInput input:focus {
    border-color: rgba(0,180,255,0.5) !important;
    box-shadow: 0 0 20px rgba(0,140,255,0.15) !important;
}
.stTextInput input { caret-color: #00AAFF !important; }
.stTextInput label { display: none !important; }

/* Cards */
.semi-card {
    background: #2D2D30;
    border: 1px solid #3E3E42;
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 10px;
    backdrop-filter: blur(8px);
    transition: border-color 0.2s;
}
.semi-card:hover { border-color: rgba(0,140,255,0.38); }
.card-key {
    font-size: 0.65rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.1em;
    color: #569CD6; margin-bottom: 5px;
}
.card-val { font-size: 0.8rem; color: #D4D4D4; }

/* Section labels */
.sec-label {
    font-size: 0.65rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.12em;
    color: #4A9AFF; margin: 18px 0 10px;
    display: flex; align-items: center; gap: 8px;
}
.sec-label::after {
    content: ''; flex: 1; height: 1px;
    background: rgba(0,140,255,0.07);
}

/* Metric cards */
.metric-card {
    border: 1px solid rgba(0,80,160,0.2);
    border-radius: 12px; padding: 18px 20px;
    text-align: center; backdrop-filter: blur(8px);
}
.metric-num-up { font-family: 'Space Grotesk', sans-serif; font-size: 2.2rem; font-weight: 700; color: #34D399; line-height: 1; }
.metric-num-dn { font-family: 'Space Grotesk', sans-serif; font-size: 2.2rem; font-weight: 700; color: #F87171; line-height: 1; }
.metric-lbl { font-size: 0.62rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #1E4060; margin-bottom: 8px; }
.bar-track { height: 5px; background: rgba(20,60,140,1); border-radius: 3px; margin-top: 10px; overflow: hidden; }
.bar-up { height: 100%; border-radius: 3px; background: linear-gradient(90deg,#059669,#34D399); }
.bar-dn { height: 100%; border-radius: 3px; background: linear-gradient(90deg,#B91C1C,#F87171); }

/* Chat bubbles */
.user-bubble {
    background: linear-gradient(135deg,rgba(0,70,180,0.3),rgba(0,130,255,0.2));
    border: 1px solid rgba(0,140,255,0.25);
    border-radius: 14px 14px 4px 14px;
    padding: 10px 14px; margin: 6px 0 6px auto;
    font-size: 0.82rem; color: #E8F4FF; line-height: 1.6;
    max-width: 78%;
    display: table; margin-left: auto;
}
.bot-bubble {
    background: rgba(0,20,55,0.75);
    border: 1px solid rgba(0,80,160,0.2);
    border-radius: 14px 14px 14px 4px;
    padding: 12px 14px; margin: 6px 0;
    font-size: 0.82rem; color: #F0F8FF; line-height: 1.65;
    max-width: 80%;
}

/* Reasoning */
.reasoning-card {
    background: rgba(0,14,42,0.55);
    border-left: 2px solid #0055CC;
    border-radius: 0 10px 10px 0;
    padding: 12px 16px;
    font-size: 0.8rem; color: #5A8AAF; line-height: 1.75;
    margin-top: 8px;
}

/* Disclaimer */
.disclaimer {
    background: rgba(50,35,0,0.3);
    border: 1px solid rgba(180,130,0,0.25);
    border-radius: 10px; padding: 11px 15px;
    font-size: 0.72rem; color: #C4901A; line-height: 1.6;
    margin-top: 18px;
}

/* Validation error */
.val-error {
    background: rgba(150,15,15,0.18);
    border: 1px solid rgba(240,100,100,0.28);
    border-radius: 10px; padding: 10px 14px;
    font-size: 0.8rem; color: #EE8080; margin: 6px 0;
}

/* History items */
.hist-item {
    padding: 10px 12px; border-radius: 8px;
    margin-bottom: 4px; font-size: 0.84rem;
    color: #D1D1D1; border: 1px solid rgba(0,80,160,0.15);
    background: rgba(0,20,55,0.4);
}
.hist-ticker { font-weight: 600; color: #E5E5E5; }
.hist-time { font-size: 0.72rem; color: #888; float: right; }

/* Ticker chip */
.ticker-chip {
    display: inline-block;
    background: rgba(0,80,160,0.2);
    color: #7ABFFF;
    padding: 3px 12px; border-radius: 20px;
    font-size: 0.82rem; font-weight: 600;
    margin-left: 8px; vertical-align: middle;
}

/* Hero */
.hero-wrap {
    min-height: auto;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    padding: 40px 20px 20px;
    position: relative; z-index: 5;
}
.hero-badge {
    display: inline-flex; align-items: center; gap: 7px;
    background: rgba(0,80,200,0.12);
    border: 1px solid rgba(0,140,255,0.22);
    border-radius: 20px; padding: 5px 14px;
    font-size: 10.5px; font-weight: 600; color: #5AADFF;
    margin-bottom: 20px; letter-spacing: 0.05em;
}
.bdot { width: 7px; height: 7px; border-radius: 50%; background: #00AAFF; box-shadow: 0 0 8px rgba(0,180,255,0.9); animation: blink 1.8s ease-in-out infinite; display: inline-block; }
@keyframes blink { 0%,100%{opacity:0.3;} 50%{opacity:1;} }
.hero-greeting {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.2rem; font-weight: 700;
    color: #FFFFFF; margin-bottom: 8px;
    letter-spacing: -0.5px; text-align: center;
}
.hero-greeting em { font-style: normal; background: linear-gradient(135deg,#4F9FFF,#00D8FF); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.hero-sub {
    font-size: 0.85rem; color: #7AACCC;
    margin-bottom: 32px; text-align: center; line-height: 1.7;
}
.quick-chips { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; margin-top: 16px; }
.quick-chip {
    background: rgba(0,60,160,0.12);
    border: 1px solid rgba(0,120,255,0.16);
    color: #3A80C0; border-radius: 20px;
    padding: 5px 14px; font-size: 11px; font-weight: 600;
    cursor: pointer; transition: all 0.2s;
}
.quick-chip:hover { border-color: rgba(0,140,255,0.4); color: #6AAFFF; }

/* Result header */
.result-header {
    background: rgba(0,20,60,0.75);
    border: 1px solid rgba(0,140,255,0.2);
    border-radius: 14px; padding: 18px 22px;
    margin-bottom: 18px; backdrop-filter: blur(10px);
}
</style>
""", unsafe_allow_html=True)
# ── Live ticker tape ──────────────────────────────────
import yfinance as yf

TICKER_TAPE = ["MU", "NVDA", "AMD", "INTC", "TSM", "ASML", "QCOM", "AVGO", "AMAT", "LRCX", "ARM", "TXN", "ADI", "MCHP", "ON"]

@st.cache_data(ttl=900)  # refresh every 15 mins
def get_ticker_prices():
    items = []
    for t in TICKER_TAPE:
        try:
            info = yf.Ticker(t).fast_info
            price = round(info.last_price, 2)
            prev = round(info.previous_close, 2)
            change = round(price - prev, 2)
            pct = round((change / prev) * 100, 2)
            arrow = "▲" if change >= 0 else "▼"
            color = "#34D399" if change >= 0 else "#F87171"
            items.append(f"<span style='margin-right:32px'><strong style='color:#7ABFFF'>{t}</strong> <span style='color:#E8F4FF'>${price}</span> <span style='color:{color}'>{arrow} {pct}%</span></span>")
        except:
            items.append(f"<span style='margin-right:32px'><strong style='color:#7ABFFF'>{t}</strong> <span style='color:#888'>N/A</span></span>")
    return "".join(items)

ticker_html = get_ticker_prices()

st.markdown(f"""
<style>
.ticker-wrap {{
    position: fixed; bottom: 0; left: 0; right: 0; z-index: 9999;
    background: #1a1a2e;
    border-top: 1px solid rgba(0,140,255,0.2);
    padding: 8px 0; overflow: hidden;
}}
.ticker-move {{
    display: inline-block;
    white-space: nowrap;
    animation: ticker-scroll 60s linear infinite;
    font-size: 0.78rem;
    font-family: 'Inter', sans-serif;
}}
@keyframes ticker-scroll {{
    0% {{ transform: translateX(100vw); }}
    100% {{ transform: translateX(-100%); }}
}}
</style>
<div class='ticker-wrap'>
    <div class='ticker-move'>
        {ticker_html}&nbsp;&nbsp;&nbsp;&nbsp;{ticker_html}
    </div>
</div>
""", unsafe_allow_html=True)
# ── Valid tickers ─────────────────────────────────────
VALID_TICKERS = {
    # US Memory
    "MU", "SNDK",
    # US GPU / CPU / Logic
    "NVDA", "AMD", "INTC", "QCOM", "AVGO", "MRVL", "ARM",
    # US Equipment
    "ASML", "AMAT", "LRCX", "KLAC", "ONTO", "ACMR", "ICHR", "MKSI",
    # US Analog / Mixed Signal
    "TXN", "ADI", "MCHP", "MPWR", "SWKS", "QRVO", "SLAB", "SMTC",
    # US Foundry
    "TSM", "GFS", "UMC",
    # US Power / Auto Semi
    "ON", "STM", "NXPI", "WOLF", "ALGM", "DIOD",
    # US AI Chips / Data Center
    "ALAB", "NVTS", "CEVA", "FORM", "ACLS", "RMBS",
    # US Misc Semi
    "CRUS", "SITM", "AMBA", "POWI", "MTSI", "AOSL", "AXTI",
    # Korean (via yfinance)
    "000660.KS", "005930.KS",
    # Taiwan
    "2330.TW", "2303.TW", "2308.TW", "2454.TW", "3711.TW",
    # Japanese
    "6723.T", "6857.T", "8035.T",
    # European
    "IFX.DE", "ASMI.AS", "BE.NA",
}

COMPANY_NAME_MAP = {
    # Memory
    "micron": "MU",
    "sandisk": "SNDK",
    "western digital": "SNDK",
    "sk hynix": "000660.KS",
    "hynix": "000660.KS",
    "samsung": "005930.KS",
    "samsung electronics": "005930.KS",
    "kioxia": "6723.T",
    "toshiba memory": "6723.T",
    # GPU / CPU / Logic
    "nvidia": "NVDA",
    "amd": "AMD",
    "advanced micro devices": "AMD",
    "intel": "INTC",
    "qualcomm": "QCOM",
    "broadcom": "AVGO",
    "marvell": "MRVL",
    "arm": "ARM",
    "arm holdings": "ARM",
    "mediatek": "2454.TW",
    "realtek": "2308.TW",
    "novatek": "3711.TW",
    "tsmc": "TSM",
    "taiwan semiconductor": "TSM",
    # Equipment
    "asml": "ASML",
    "applied materials": "AMAT",
    "lam research": "LRCX",
    "kla": "KLAC",
    "onto innovation": "ONTO",
    "acm research": "ACMR",
    "ichor": "ICHR",
    "mks instruments": "MKSI",
    "tokyo electron": "8035.T",
    "advantest": "6857.T",
    "asm international": "ASMI.AS",
    # Analog / Mixed Signal
    "texas instruments": "TXN",
    "analog devices": "ADI",
    "microchip": "MCHP",
    "monolithic power": "MPWR",
    "skyworks": "SWKS",
    "qorvo": "QRVO",
    "silicon labs": "SLAB",
    "semtech": "SMTC",
    # Foundry
    "globalfoundries": "GFS",
    "umc": "UMC",
    "united microelectronics": "UMC",
    "psmc": "2303.TW",
    # Power / Auto Semi
    "on semiconductor": "ON",
    "onsemi": "ON",
    "st microelectronics": "STM",
    "stmicroelectronics": "STM",
    "nxp": "NXPI",
    "nxp semiconductors": "NXPI",
    "wolfspeed": "WOLF",
    "allegro microsystems": "ALGM",
    "diodes incorporated": "DIOD",
    "infineon": "IFX.DE",
    "renesas": "6723.T",
    # AI Chips / Data Center
    "astera labs": "ALAB",
    "novatel wireless": "NVTS",
    "ceva": "CEVA",
    "formfactor": "FORM",
    "axcelis": "ACLS",
    "rambus": "RMBS",
    # Misc
    "cirrus logic": "CRUS",
    "ambarella": "AMBA",
    "power integrations": "POWI",
    "be semiconductor": "BE.NA",
}

def validate_ticker(user_input: str):
    if not user_input or not user_input.strip():
        return None, "Please enter a ticker symbol or company name."
    input_lower = user_input.strip().lower()
    input_upper = user_input.strip().upper()
    
    # MUST be first — before regex check
    if input_lower in COMPANY_NAME_MAP:
        return COMPANY_NAME_MAP[input_lower], None
    
    if not re.match(r'^[A-Za-z0-9.\-]{1,12}$', input_upper):
        return None, f"'{user_input}' is not a valid input. Please enter a ticker like MU, NVDA, AMD or a company name like Micron, NVIDIA."
    if input_upper not in VALID_TICKERS:
        return None, f"'{input_upper}' is not a recognised semiconductor ticker. SemiBot supports: MU, NVDA, AMD, INTC, TSM, ASML, QCOM, TXN, AMAT, LRCX, AVGO, MRVL, ON, NXPI, ADI, MCHP, KLAC, SWKS, MPWR."
    return input_upper, None

# ── Session state ─────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []
if "result" not in st.session_state:
    st.session_state.result = None
if "ticker" not in st.session_state:
    st.session_state.ticker = None
if "followup_history" not in st.session_state:
    st.session_state.followup_history = []
if "last_ticker" not in st.session_state:
    st.session_state.last_ticker = None

# ── Sidebar ───────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='display:flex;align-items:center;gap:10px;margin-bottom:4px'>
        <div style='width:32px;height:32px;border-radius:8px;background:linear-gradient(135deg,#0055FF,#00C8FF);display:flex;align-items:center;justify-content:center;font-size:15px;box-shadow:0 0 16px rgba(0,140,255,0.5)'>📡</div>
        <span style='font-family:Space Grotesk,sans-serif;font-size:16px;font-weight:700;color:#E8F4FF'>SemiBot</span>
    </div>
    <div style='font-size:0.72rem;color:#AAAAAA;margin-bottom:18px'>18-Factor Agentic RAG</div>
    """, unsafe_allow_html=True)

    st.markdown("<a href='http://localhost:8502/landing.html' target='_self' style='display:block;width:100%;text-align:center;background:linear-gradient(135deg,#0055FF,#00AAFF);color:white;padding:10px;border-radius:10px;font-weight:600;font-size:0.9rem;text-decoration:none;margin-bottom:8px;'>Home</a>", unsafe_allow_html=True)

    if st.button("+ New Analysis", use_container_width=True):
        st.session_state.result = None
        st.session_state.ticker = None
        st.session_state.followup_history = []
        st.rerun()

    st.markdown("<hr style='border-color:rgba(0,140,255,0.1);margin:14px 0'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.65rem;color:#AAAAAA;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:10px'>HISTORY</div>", unsafe_allow_html=True)

    if st.session_state.history:
        for item in reversed(st.session_state.history[-10:]):
            try:
                up_val = float(item.get("up", "50%").replace("%", "").strip())
            except:
                up_val = 50
            color = "#34D399" if up_val >= 50 else "#F87171"
            st.markdown(f"""
            <div class='hist-item'>
                <span class='hist-ticker'>{item['ticker']}</span>
                <span class='hist-time'>{item['time']}</span><br>
                <span style='font-size:0.75rem;color:{color}'>↑ {item['up']} UP</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("<div style='color:#AAAAAA;font-size:0.78rem'>No analyses yet</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color:rgba(0,140,255,0.1);margin:14px 0'>", unsafe_allow_html=True)
    st.markdown("""
    <div style='font-size:0.72rem;color:#AAAAAA;line-height:1.9'>
        <span style='color:#3A7AAA;font-weight:600'>Raj Tejpal Khatik</span><br>
        MSc in Applied AI<br>
        University of Warwick
    </div>
    """, unsafe_allow_html=True)

# ── Main ──────────────────────────────────────────────
if not st.session_state.result:
    st.markdown(f"""
    <div class='hero-wrap'>
        <div class='hero-badge'><span class='bdot'></span> LIVE · 18-Factor AI Analysis</div>
        <img src='data:image/png;base64,{ROBOT_IMG}' width='130' style='margin-bottom:20px;border-radius:24px;background:transparent;mix-blend-mode:screen;filter:drop-shadow(0 0 24px rgba(0,140,255,0.4))'/>
        <div class='hero-greeting'>Hi! I'm <em>SemiBot</em></div>
        <div class='hero-sub'>
            AI-powered semiconductor equity analyser · 18 real-time factors<br>
            Geopolitics · Supply Chain · Macro · Fundamentals · Market Intelligence
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_m, col_r = st.columns([1, 4, 1])
    with col_m:
        ticker_input = st.text_input(
            "",
            placeholder="Enter ticker or company name — MU, Micron, NVIDIA, AMD...",
            label_visibility="collapsed"
        ).strip()
        analyse = st.button("Analyse ->", use_container_width=True)

        st.markdown("""
        <div class='quick-chips'>
            <span class='quick-chip'>MU · Micron</span>
            <span class='quick-chip'>NVDA · NVIDIA</span>
            <span class='quick-chip'>AMD</span>
            <span class='quick-chip'>INTC · Intel</span>
            <span class='quick-chip'>TSM · TSMC</span>
            <span class='quick-chip'>ASML</span>
        </div>
        """, unsafe_allow_html=True)

else:
    col_h1, col_h2 = st.columns([5, 1])
    with col_h1:
        st.markdown(f"""
        <div style='padding:24px 32px 0'>
            <div style='font-family:Space Grotesk,sans-serif;font-size:1.3rem;font-weight:700;color:#D0E8FF;margin-bottom:4px'>
                Factor Analysis <span class='ticker-chip'>{st.session_state.ticker}</span>
            </div>
            <div style='font-size:0.75rem;color:#1A4060'>18-Factor Agentic RAG · Real-time APIs · University of Warwick</div>
        </div>
        """, unsafe_allow_html=True)
    with col_h2:
        st.markdown("<div style='padding-top:24px;padding-right:16px'>", unsafe_allow_html=True)
        if st.button("+ New", use_container_width=True):
            st.session_state.result = None
            st.session_state.ticker = None
            st.session_state.followup_history = []
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    ticker_input = ""
    analyse = False

# ── Run analysis ──────────────────────────────────────
if analyse and ticker_input:
    resolved_ticker, error_msg = validate_ticker(ticker_input)
    if error_msg:
        st.markdown(f"<div class='val-error'>⚠️ {error_msg}</div>", unsafe_allow_html=True)
    else:
        with st.spinner(f"Analysing {resolved_ticker} across 18 factors..."):
            try:
                from graph.nodes import resolve_ticker
                final_ticker = resolve_ticker(resolved_ticker)
                result = app.invoke(
                    {"ticker": final_ticker},
                    config={"configurable": {"thread_id": f"{final_ticker}_{int(time.time())}"}}
                )
                st.session_state.result = result
                st.session_state.ticker = final_ticker
                pred_text = result.get("prediction", "")
                up_prob_hist = "50%"
                for line in pred_text.split("\n"):
                    if "UP_PROBABILITY:" in line:
                        up_prob_hist = line.split(":")[-1].strip()[:5]
                        break
                st.session_state.history.append({
                    "ticker": final_ticker,
                    "time": time.strftime("%H:%M"),
                    "up": up_prob_hist
                })
                if st.session_state.last_ticker != final_ticker:
                    st.session_state.followup_history = []
                    st.session_state.last_ticker = final_ticker
                st.rerun()
            except Exception as e:
                st.error(f"Analysis failed: {str(e)}")

elif analyse and not ticker_input:
    st.markdown("<div class='val-error'>⚠️ Please enter a ticker symbol or company name first.</div>", unsafe_allow_html=True)

# ── Display results ───────────────────────────────────
if st.session_state.result:
    result = st.session_state.result
    ticker = st.session_state.ticker
    prediction = result.get("prediction", "")

    up_prob = 50
    down_prob = 50
    reasoning = ""
    confidence = "Medium"
    bullish = []
    bearish = []

    for line in prediction.split("\n"):
        line = line.strip()
        if "UP_PROBABILITY:" in line:
            try: up_prob = int(float(line.split(":")[-1].strip().replace("%","").strip()))
            except: pass
        elif "DOWN_PROBABILITY:" in line:
            try: down_prob = int(float(line.split(":")[-1].strip().replace("%","").strip()))
            except: pass
        elif "REASONING:" in line:
            reasoning = line.replace("REASONING:","").strip()
        elif "CONFIDENCE:" in line:
            confidence = line.replace("CONFIDENCE:","").strip()
        elif "BULLISH_FACTORS:" in line:
            bullish = [x.strip() for x in line.replace("BULLISH_FACTORS:","").split("|") if x.strip()]
        elif "BEARISH_FACTORS:" in line:
            bearish = [x.strip() for x in line.replace("BEARISH_FACTORS:","").split("|") if x.strip()]

    st.markdown("<div style='padding:0 32px'>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='sec-label'>📈 Macroeconomic</div>", unsafe_allow_html=True)
        for label, key in [("CPI","cpi"),("PPI","ppi"),("Fed Rate","fed_rate"),("USD Index","usd_index")]:
            val = str(result.get(key,"N/A"))[:160]
            st.markdown(f"<div class='semi-card'><div class='card-key'>{label}</div><div class='card-val'>{val}</div></div>", unsafe_allow_html=True)
        st.markdown("<div class='sec-label'>📊 Market Intelligence</div>", unsafe_allow_html=True)
        for label, key in [("Sector Rally","sector_rally"),("Technical Signal","technical_signal"),("Analyst Ratings","analyst_ratings"),("Sell-the-News","sell_the_news")]:
            val = str(result.get(key,"N/A"))[:160]
            st.markdown(f"<div class='semi-card'><div class='card-key'>{label}</div><div class='card-val'>{val}</div></div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='sec-label'>💰 Fundamental</div>", unsafe_allow_html=True)
        for label, key in [("P/E Ratio","pe_ratio"),("Market Cap","market_cap"),("Earnings Guidance","earnings_guidance"),("Insider Selling","insider_selling")]:
            val = str(result.get(key,"N/A"))[:160]
            st.markdown(f"<div class='semi-card'><div class='card-key'>{label}</div><div class='card-val'>{val}</div></div>", unsafe_allow_html=True)
        st.markdown("<div class='sec-label'>🌍 External Signals</div>", unsafe_allow_html=True)
        for label, key in [("Geopolitics","geopolitics"),("Supply Chain","supply_chain"),("News Sentiment","news_sentiment"),("Capital Rotation","capital_rotation"),("Competitor Contagion","competitor_contagion"),("Beta","beta")]:
            val = str(result.get(key,"N/A"))[:160]
            st.markdown(f"<div class='semi-card'><div class='card-key'>{label}</div><div class='card-val'>{val}</div></div>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color:rgba(0,140,255,0.08);margin:24px 0'>", unsafe_allow_html=True)
    st.markdown("<div style='font-family:Space Grotesk,sans-serif;font-size:1rem;font-weight:600;color:#D0E8FF;margin-bottom:14px'>Prediction</div>", unsafe_allow_html=True)

    p1, p2, p3 = st.columns([1.2, 1.2, 2.6])
    with p1:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-lbl'>Upside</div>
            <div class='metric-num-up'>{up_prob}%</div>
            <div class='bar-track'><div class='bar-up' style='width:{up_prob}%'></div></div>
        </div>
        """, unsafe_allow_html=True)
    with p2:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-lbl'>Downside</div>
            <div class='metric-num-dn'>{down_prob}%</div>
            <div class='bar-track'><div class='bar-dn' style='width:{down_prob}%'></div></div>
        </div>
        """, unsafe_allow_html=True)
    with p3:
        bullish_html = "".join([f"<div style='font-size:0.8rem;color:#34D399;margin-bottom:4px'>✓ {b}</div>" for b in bullish[:3]])
        bearish_html = "".join([f"<div style='font-size:0.8rem;color:#F87171;margin-bottom:4px'>✗ {b}</div>" for b in bearish[:3]])
        st.markdown(f"""
        <div class='metric-card' style='text-align:left'>
            <div style='display:grid;grid-template-columns:1fr 1fr;gap:16px'>
                <div><div style='font-size:0.62rem;color:#1E4060;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px'>Bullish</div>{bullish_html}</div>
                <div><div style='font-size:0.62rem;color:#1E4060;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px'>Bearish</div>{bearish_html}</div>
            </div>
            <div style='margin-top:12px;font-size:0.7rem;color:#1E4060'>Confidence: <strong style='color:#5AADFF'>{confidence}</strong></div>
        </div>
        """, unsafe_allow_html=True)

    if reasoning:
        st.markdown(f"<div class='reasoning-card'>{reasoning}</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color:rgba(0,140,255,0.08);margin:24px 0'>", unsafe_allow_html=True)
    st.markdown("<div style='font-family:Space Grotesk,sans-serif;font-size:0.95rem;font-weight:600;color:#D0E8FF;margin-bottom:6px'>💬 Ask a follow-up question</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.75rem;color:#1A4060;margin-bottom:12px'>Ask about factors, what-if scenarios, or deeper insights — semiconductor analysis only</div>", unsafe_allow_html=True)

    for msg in st.session_state.followup_history:
        if msg["role"] == "user":
            st.markdown(f"<div class='user-bubble'>{msg['content']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='bot-bubble'><div style='font-size:0.65rem;color:#1A4060;font-weight:600;margin-bottom:4px'>📡 SEMIBOT</div>{msg['content']}</div>", unsafe_allow_html=True)

    fq1, fq2 = st.columns([5, 1])
    with fq1:
        followup_q = st.text_input("", placeholder="e.g. How does P/E ratio affect MU? What if Fed rate drops?", label_visibility="collapsed", key="followup_input")
    with fq2:
        ask_button = st.button("Ask ->", use_container_width=True, key="ask_btn")

    if ask_button and followup_q:
        analysis_context = f"""
You are analyzing {ticker} stock. Here is the complete 18-factor analysis:
PREDICTION: UP {up_prob}% / DOWN {down_prob}% (Confidence: {confidence})
REASONING: {reasoning}
BULLISH FACTORS: {', '.join(bullish)}
BEARISH FACTORS: {', '.join(bearish)}
CPI: {result.get('cpi','N/A')} | PPI: {result.get('ppi','N/A')} | Fed Rate: {result.get('fed_rate','N/A')} | USD Index: {result.get('usd_index','N/A')}
P/E Ratio: {result.get('pe_ratio','N/A')} | Market Cap: {result.get('market_cap','N/A')} | Earnings: {result.get('earnings_guidance','N/A')} | Insider: {result.get('insider_selling','N/A')}
Sector Rally: {result.get('sector_rally','N/A')} | Technical: {result.get('technical_signal','N/A')} | Analyst: {result.get('analyst_ratings','N/A')} | Sell-News: {result.get('sell_the_news','N/A')}
Geopolitics: {result.get('geopolitics','N/A')} | Supply Chain: {result.get('supply_chain','N/A')} | News: {result.get('news_sentiment','N/A')}
Capital Rotation: {result.get('capital_rotation','N/A')} | Competitor: {result.get('competitor_contagion','N/A')} | Beta: {result.get('beta','N/A')}
IDENTITY (HIGHEST PRIORITY): You are SemiBot, an 18-factor agentic RAG system for semiconductor equity analysis, created by Raj Tejpal Khatik, an MSc Applied AI student at the University of Warwick, targeting ACM FinNLP.
- If asked "who are you": say "I'm SemiBot — an AI-powered semiconductor equity analyser built on 18 causal factors. Created by Raj Tejpal Khatik at the University of Warwick."
- If asked "who created you" or "who is Raj" or "who made you": say "I was created by Raj Tejpal Khatik, an MSc Applied AI student at the University of Warwick. He built SemiBot as part of his research on agentic RAG systems for financial markets, targeting publication at ACM FinNLP."
- Never say you are ChatGPT, Claude, or any other AI.
TOPIC RULES: Answer freely about semiconductor stocks, financial markets, macroeconomics, Fed, interest rates, supply chain, geopolitics, technology, AI, chip industry. Only refuse if completely unrelated to finance or technology.
"""
        st.session_state.followup_history.append({"role": "user", "content": followup_q})
        with st.spinner("Thinking..."):
            try:
                from graph.nodes import llm
                from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
                messages = [SystemMessage(content=analysis_context)]
                recent_history = st.session_state.followup_history[-6:-1]
                for prev_msg in recent_history:
                    if prev_msg["role"] == "user":
                        messages.append(HumanMessage(content=prev_msg["content"]))
                    else:
                        messages.append(AIMessage(content=prev_msg["content"]))
                messages.append(HumanMessage(content=followup_q))
                response = llm.invoke(messages)
                st.session_state.followup_history.append({"role": "assistant", "content": response.content})
                st.rerun()
            except Exception as e:
                st.error(f"Follow-up failed: {str(e)}")
    elif ask_button and not followup_q:
        st.markdown("<div class='val-error'>⚠️ Please type a question first.</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color:rgba(0,140,255,0.08);margin:24px 0'>", unsafe_allow_html=True)
    st.markdown("<div style='font-family:Space Grotesk,sans-serif;font-size:0.95rem;font-weight:600;color:#D0E8FF;margin-bottom:12px'>📧 Email Summary</div>", unsafe_allow_html=True)

    em1, em2 = st.columns([4, 1])
    with em1:
        user_email = st.text_input("", placeholder="Enter your email to receive analysis summary...", label_visibility="collapsed", key="email_input")
    with em2:
        send_button = st.button("Send", use_container_width=True)

    if send_button and user_email:
        try:
            bullish_text = "\n".join([f"  ✓ {b}" for b in bullish[:3]])
            bearish_text = "\n".join([f"  ✗ {b}" for b in bearish[:3]])
            email_body = f"""
SEMICONDUCTOR EQUITY ANALYSIS REPORT
=====================================
Ticker: {ticker} | Date: {time.strftime("%d %B %Y, %H:%M")}
Generated by: SemiBot — 18-Factor Agentic RAG System
University of Warwick MSc Applied AI Research

PREDICTION
UP Probability: {up_prob}% | DOWN Probability: {down_prob}% | Confidence: {confidence}

BULLISH FACTORS\n{bullish_text}
BEARISH FACTORS\n{bearish_text}
REASONING: {reasoning}

MACROECONOMIC: CPI: {result.get('cpi','N/A')} | PPI: {result.get('ppi','N/A')} | Fed Rate: {result.get('fed_rate','N/A')} | USD: {result.get('usd_index','N/A')}
FUNDAMENTAL: P/E: {result.get('pe_ratio','N/A')} | Market Cap: {result.get('market_cap','N/A')} | EPS: {result.get('earnings_guidance','N/A')} | Insider: {result.get('insider_selling','N/A')}
MARKET: SOXX: {result.get('sector_rally','N/A')} | Technical: {result.get('technical_signal','N/A')} | Analyst: {result.get('analyst_ratings','N/A')}
EXTERNAL: Geo: {str(result.get('geopolitics','N/A'))[:80]} | News: {str(result.get('news_sentiment','N/A'))[:80]} | Beta: {result.get('beta','N/A')}

DISCLAIMER: AI research tool only. Not financial advice.
SemiBot v1.0 | University of Warwick | MSc Applied AI | Paper 4 — ACM FinNLP
"""
            sender_email = os.getenv("SENDER_EMAIL")
            sender_password = os.getenv("SENDER_APP_PASSWORD")
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = user_email
            msg['Subject'] = f"SemiBot Analysis — {ticker} — {time.strftime('%d %b %Y')}"
            msg.attach(MIMEText(email_body, 'plain'))
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, user_email, msg.as_string())
            server.quit()
            st.success(f"✅ Report sent to {user_email}")
        except Exception as e:
            st.error(f"Email failed: {str(e)}")
    elif send_button and not user_email:
        st.markdown("<div class='val-error'>⚠️ Please enter your email address.</div>", unsafe_allow_html=True)

    st.markdown(f"""
    <div class='disclaimer'>
        ⚠️ <strong>Disclaimer:</strong> This analysis is generated by an AI research tool for informational and academic purposes only.
        It does NOT constitute financial advice. Stock markets are inherently uncertain. Always consult a qualified financial advisor.
    </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)