import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "SemiBot"

import sys
import re
# PATH FIX 1: Go up TWO levels (pages/ -> frontend/ -> SEMIBOT/) instead of one
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st

# Show a loading message IMMEDIATELY so users don't see a blank page while
# the heavy imports below (LangGraph, FAISS, HuggingFace embeddings,
# yfinance) run on first visit. Cleared at the end of the script.
_loading_placeholder = st.empty()
_loading_placeholder.markdown(
    """
    <div style="position:fixed;inset:0;display:flex;align-items:center;justify-content:center;
                background:#171B21;z-index:999999;flex-direction:column;gap:14px;">
      <div style="width:44px;height:44px;border:3px solid rgba(91,155,255,.2);
                  border-top-color:#5B9BFF;border-radius:50%;
                  animation:sb-spin 0.9s linear infinite;"></div>
      <div style="color:#C7D1DF;font-family:Inter,sans-serif;font-size:14px;">
        Loading SemiBot analysis engine…
      </div>
      <style>@keyframes sb-spin{to{transform:rotate(360deg)}}</style>
    </div>
    """,
    unsafe_allow_html=True,
)

import time
from zoneinfo import ZoneInfo
from datetime import datetime

UK_TZ = ZoneInfo("Europe/London")

def uk_time_str():
    return datetime.now(UK_TZ).strftime("%Y-%m-%d %H:%M")
import smtplib
import yfinance as yf
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from graph.workflow import app, build_graph
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from log_client import log_event
from chat_bubble import render_chat_bubble, _live_price_block
from causal_map import render_causal_map, FACTOR_KEYS
from extras import (
    render_ticker_logo,
    get_ticker_from_query,
    set_ticker_in_query,
    render_copy_link_button,
    render_download_pdf_button,
)

# PATH FIX 2: Go up TWO levels to find .env at project root
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env'))
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "true")
os.environ["LANGCHAIN_API_KEY"]     = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_PROJECT"]     = os.getenv("LANGCHAIN_PROJECT", "SemiBot")
import time as _time
_t0 = _time.time()
print(f"[TIMING] Script start", flush=True)

import base64
# PATH FIX 3: Go up ONE level (pages/ -> frontend/) to find static/robot_b64.txt
with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'robot_b64.txt'), 'r') as f:
    ROBOT_IMG = f.read()
print(f"[TIMING] After robot image load: {_time.time() - _t0:.2f}s", flush=True)

def score_badge(key, scores):
    score = scores.get(key)
    if score is None:
        return ""
    if score > 0:
        color = "#34D399"
        label = "Bullish"
    elif score < 0:
        color = "#F87171"
        label = "Bearish"
    else:
        color = "#9AA6B8"
        label = "Neutral"
    sign = "+" if score > 0 else ""
    return f"<div style='margin-top:6px;font-size:0.75rem;font-weight:600'><span style='color:#9AA6B8'>Score: </span><span style='color:{color}'>{sign}{score}</span><span style='color:{color};margin-left:6px'>{label}</span></div>"

def smart_truncate(text, limit: int = 1200) -> str:
    """
    Truncates text at the nearest sentence boundary near `limit`,
    so cards always show complete sentences instead of cutting mid-word.
    """
    text = str(text)
    if len(text) <= limit:
        return text

    window = text[:limit + 80]
    for punct in ['. ', '! ', '? ']:
        idx = window.rfind(punct, 0, limit + 80)
        if idx != -1 and idx > limit * 0.5:
            return window[:idx + 1].strip()

    cut = text[:limit].rsplit(' ', 1)[0]
    return cut.strip() + "..."

def parse_result(result: dict):
    prediction = result.get("prediction", "")
    up_prob, down_prob, confidence, reasoning = 50, 50, "Medium", ""
    bullish, bearish = [], []
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
    return {"up_prob": up_prob, "down_prob": down_prob, "confidence": confidence,
            "reasoning": reasoning, "bullish": bullish, "bearish": bearish}

import sqlite3
import json

def get_db_path():
    # PATH FIX 4: Go up TWO levels to find semibot_checkpoints.db at project root
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'semibot_checkpoints.db')

def init_history_table():
    conn = sqlite3.connect(get_db_path())
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT,
            up_prob TEXT,
            timestamp TEXT,
            result_json TEXT,
            followup_json TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_history(ticker, up_prob, timestamp, result, followup_history):
    conn = sqlite3.connect(get_db_path())
    conn.execute(
        "INSERT INTO analysis_history (ticker, up_prob, timestamp, result_json, followup_json) VALUES (?, ?, ?, ?, ?)",
        (ticker, up_prob, timestamp, json.dumps(result), json.dumps(followup_history))
    )
    conn.commit()
    conn.close()

def load_history(limit=10):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.execute(
        "SELECT id, ticker, up_prob, timestamp FROM analysis_history ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "ticker": r[1], "up": r[2], "time": r[3]} for r in rows]

def load_history_detail(history_id):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.execute(
        "SELECT ticker, result_json, followup_json FROM analysis_history WHERE id = ?",
        (history_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0], json.loads(row[1]), json.loads(row[2])
    return None, None, None

def update_followup(history_id, followup_history):
    conn = sqlite3.connect(get_db_path())
    conn.execute(
        "UPDATE analysis_history SET followup_json = ? WHERE id = ?",
        (json.dumps(followup_history), history_id)
    )
    conn.commit()
    conn.close()

def init_compare_table():
    conn = sqlite3.connect(get_db_path())
    conn.execute("""
        CREATE TABLE IF NOT EXISTS compare_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tickers_csv TEXT,
            timestamp TEXT,
            results_json TEXT,
            followup_json TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_compare_session(tickers_list, timestamp, results_dict, followup_history):
    conn = sqlite3.connect(get_db_path())
    conn.execute(
        "INSERT INTO compare_sessions (tickers_csv, timestamp, results_json, followup_json) VALUES (?, ?, ?, ?)",
        (",".join(tickers_list), timestamp, json.dumps(results_dict), json.dumps(followup_history))
    )
    conn.commit()
    conn.close()

def load_compare_sessions(limit=10):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.execute(
        "SELECT id, tickers_csv, timestamp FROM compare_sessions ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "tickers_csv": r[1], "time": r[2]} for r in rows]

def load_compare_session_detail(session_id):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.execute(
        "SELECT tickers_csv, results_json, followup_json FROM compare_sessions WHERE id = ?",
        (session_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0].split(","), json.loads(row[1]), json.loads(row[2])
    return None, None, None

def update_compare_followup(session_id, followup_history):
    conn = sqlite3.connect(get_db_path())
    conn.execute(
        "UPDATE compare_sessions SET followup_json = ? WHERE id = ?",
        (json.dumps(followup_history), session_id)
    )
    conn.commit()
    conn.close()

def get_historical_context(ticker, limit=5):
    """Long-term memory: queries past analysis sessions for this SAME ticker from SQLite
    (persists across threads/sessions) and returns a trend summary the agent can reason over."""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.execute(
        "SELECT up_prob, timestamp FROM analysis_history WHERE ticker = ? ORDER BY id DESC LIMIT ?",
        (ticker, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return f"No prior analysis history for {ticker} yet."
    summary_lines = [f"UP {up} at {ts}" for up, ts in rows]
    return f"Recent {ticker} analysis history (most recent first): {'; '.join(summary_lines)}."

init_history_table()
init_compare_table()

TICKER_TAPE = ["MU", "NVDA", "AMD", "INTC", "TSM", "ASML", "QCOM", "AVGO", "AMAT", "LRCX", "ARM", "TXN", "ADI", "MCHP", "ON"]

@st.cache_data(ttl=900)
def get_ticker_prices():
    try:
        data = yf.download(tickers=" ".join(TICKER_TAPE), period="5d", interval="1d", group_by="ticker", threads=True, progress=False)
        results = []
        for t in TICKER_TAPE:
            try:
                closes = data[t]["Close"].dropna()
                if len(closes) < 2:
                    raise ValueError("not enough price history")
                price = round(float(closes.iloc[-1]), 2)
                prev = round(float(closes.iloc[-2]), 2)
                change = round(price - prev, 2)
                pct = round((change / prev) * 100, 2)
                arrow = "▲" if change >= 0 else "▼"
                color = "#34D399" if change >= 0 else "#F87171"
                results.append(f"<span style='margin-right:32px'><strong style='color:#8BB8FF'>{t}</strong> <span style='color:#EDF0F5'>${price}</span> <span style='color:{color}'>{arrow} {pct}%</span></span>")
            except Exception as e:
                print(f"[TICKER ERROR] {t}: {e}", flush=True)
                results.append(f"<span style='margin-right:32px'><strong style='color:#8BB8FF'>{t}</strong> <span style='color:#9AA6B8'>N/A</span></span>")
        return "".join(results)
    except Exception as e:
        print(f"[TICKER TAPE BATCH ERROR]: {e}", flush=True)
        return "".join(f"<span style='margin-right:32px'><strong style='color:#8BB8FF'>{t}</strong> <span style='color:#9AA6B8'>N/A</span></span>" for t in TICKER_TAPE)

def render_ticker_tape():
    ticker_html = get_ticker_prices()
    st.markdown(f"""
    <style>
    .ticker-wrap {{
        position: fixed; bottom: 0; left: 0; right: 0; z-index: 9999;
        background: #262F3E;
        border-top: 1px solid #3A4658;
        padding: 8px 0; overflow: hidden;
    }}
    .ticker-move {{
        display: inline-block; white-space: nowrap;
        animation: ticker-scroll 60s linear infinite;
        font-size: 0.78rem; font-family: 'Inter', sans-serif;
    }}
    @keyframes ticker-scroll {{
        0% {{ transform: translateX(100vw); }}
        100% {{ transform: translateX(-100%); }}
    }}
    </style>
    <div class='ticker-wrap'>
        <div class='ticker-move'>{ticker_html}&nbsp;&nbsp;&nbsp;&nbsp;{ticker_html}</div>
    </div>
    """, unsafe_allow_html=True)

st.set_page_config(
    page_title="SemiBot",
    page_icon="::",
    layout="wide",
    initial_sidebar_state="expanded"
)



st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
    --bg:#1E2633; --surface:#262F3E; --surface-2:#2D3849; --line:#3A4658; --line-2:#4A5870;
    --text:#EDF0F5; --text-2:#C2CAD6; --text-3:#9AA6B8;
    --accent:#5B9BFF; --accent-hi:#8BB8FF; --accent-ink:#06101F; --accent-soft:rgba(91,155,255,0.12);
    --up:#34D399; --down:#F87171; --warn:#FBBF24;
    --mono:'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}

html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"], .stApp {
    background: var(--bg) !important;
    font-family: 'Inter', system-ui, sans-serif !important;
    color: var(--text);
}
.stSpinner > div { color: var(--text) !important; }
[data-testid="stStatusWidget"] { color: var(--text) !important; }
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
[data-testid="stDecoration"] { display: none; }
.block-container { padding: 0 !important; padding-bottom: 72px !important; max-width: 1180px !important; margin: 0 auto !important; }
:focus-visible { outline: 2px solid var(--accent-hi) !important; outline-offset: 2px; }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--line) !important;
    min-width: 260px !important;
    max-width: 260px !important;
    display: flex !important;
    transform: none !important;
}
[data-testid="collapsedControl"] { display: none !important; }
[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] { display: none !important; }
[data-testid="stSidebarNav"] { display: none !important; }
[data-testid="stSidebar"] * { color: var(--text) !important; }
[data-testid="stSidebarContent"] { padding: 22px 16px !important; }
[data-testid="stSidebar"] .stButton > button,
[data-testid="stSidebar"] [data-testid="stPageLink"] a {
    background: transparent !important;
    border: 1px solid var(--line) !important;
    color: var(--text-2) !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    justify-content: flex-start !important;
    text-align: left !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] .stButton > button:hover,
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
    background: var(--surface-2) !important;
    border-color: var(--line-2) !important;
}

/* ---------- buttons ---------- */
.stButton > button {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
    transition: background 0.15s, border-color 0.15s, transform 0.15s !important;
    min-height: 44px;
    background: transparent !important;
    border: 1px solid var(--line-2) !important;
    color: var(--text) !important;
}
.stButton > button:hover { border-color: var(--accent) !important; background: var(--accent-soft) !important; }
.stButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"] {
    background: var(--accent) !important;
    border: 1px solid var(--accent) !important;
    color: var(--accent-ink) !important;
}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="stBaseButton-primary"]:hover {
    background: var(--accent-hi) !important;
    border-color: var(--accent-hi) !important;
    transform: translateY(-1px);
}
.stButton > button[kind="primary"] p,
.stButton > button[data-testid="stBaseButton-primary"] p { color: var(--accent-ink) !important; }

/* ---------- inputs ---------- */
.stTextInput input {
    background: var(--surface) !important;
    border: 1px solid var(--line-2) !important;
    border-radius: 10px !important;
    padding: 12px 16px !important;
    color: var(--text) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.95rem !important;
    caret-color: var(--accent-hi) !important;
}
.stTextInput input::placeholder { color: var(--text-3) !important; }
.stTextInput input:focus { border-color: var(--accent) !important; box-shadow: 0 0 0 3px var(--accent-soft) !important; }
.stTextInput label { display: none !important; }
[data-baseweb="select"] > div {
    background: var(--surface) !important;
    border: 1px solid var(--line-2) !important;
    border-radius: 10px !important;
    min-height: 46px;
}
[data-baseweb="select"] > div:focus-within { border-color: var(--accent) !important; box-shadow: 0 0 0 3px var(--accent-soft) !important; }
[data-baseweb="select"] * { color: var(--text) !important; }
[data-testid="stWidgetLabel"] p { color: var(--text-2) !important; font-weight: 500 !important; }

/* ---------- factor cards ---------- */
.semi-card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 10px;
    transition: border-color 0.15s;
}
.semi-card:hover { border-color: var(--line-2); }
.semi-card.hover-expand { position: relative; cursor: help; }
.semi-card.hover-expand .hover-tooltip {
    display: none;
    position: absolute;
    z-index: 1000;
    top: 100%;
    left: 0;
    width: 340px;
    max-width: 90vw;
    margin-top: 6px;
    background: var(--surface-2);
    border: 1px solid var(--line-2);
    border-radius: 10px;
    padding: 14px 16px;
    font-size: 0.82rem;
    line-height: 1.65;
    color: var(--text);
    box-shadow: 0 12px 32px rgba(0,0,0,0.6);
}
.semi-card.hover-expand:hover .hover-tooltip { display: block; }
.card-key {
    font-family: var(--mono);
    font-size: 0.68rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.08em;
    color: var(--accent-hi); margin-bottom: 6px;
}
.card-val { font-size: 0.88rem; color: var(--text-2); line-height: 1.65; }

.sec-label {
    font-family: var(--mono);
    font-size: 0.72rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.1em;
    color: var(--text-3); margin: 26px 0 12px;
    display: flex; align-items: center; gap: 12px;
}
.sec-label::after { content: ''; flex: 1; height: 1px; background: var(--line); }

/* ---------- prediction ---------- */
.metric-card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 12px; padding: 18px 20px;
    text-align: center;
}
.metric-num-up, .metric-num-dn { font-family: var(--mono); font-size: 2.3rem; font-weight: 600; line-height: 1; font-variant-numeric: tabular-nums; }
.metric-num-up { color: var(--up); }
.metric-num-dn { color: var(--down); }
.metric-lbl { font-family: var(--mono); font-size: 0.68rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-3); margin-bottom: 10px; }
.bar-track { height: 6px; background: var(--line); border-radius: 99px; margin-top: 14px; overflow: hidden; }
.bar-up { height: 100%; border-radius: 99px; background: var(--up); }
.bar-dn { height: 100%; border-radius: 99px; background: var(--down); }

.reasoning-card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-left: 3px solid var(--accent);
    border-radius: 0 10px 10px 0;
    padding: 14px 18px;
    font-size: 0.88rem; color: var(--text-2); line-height: 1.75;
    margin-top: 12px;
}

/* ---------- follow-up chat ---------- */
.user-bubble {
    background: var(--accent-soft);
    border: 1px solid rgba(91,155,255,0.3);
    border-radius: 14px 14px 4px 14px;
    padding: 10px 14px; margin: 6px 0 6px auto;
    font-size: 0.88rem; color: var(--text); line-height: 1.6;
    max-width: 78%; display: table; margin-left: auto;
}
.bot-bubble {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 14px 14px 14px 4px;
    padding: 12px 14px; margin: 6px 0;
    font-size: 0.88rem; color: var(--text); line-height: 1.65;
    max-width: 82%;
}

.disclaimer {
    background: rgba(251,191,36,0.07);
    border: 1px solid rgba(251,191,36,0.3);
    border-radius: 10px; padding: 12px 16px;
    font-size: 0.78rem; color: #E8C468; line-height: 1.6;
    margin-top: 22px;
}
.val-error {
    background: rgba(248,113,113,0.08);
    border: 1px solid rgba(248,113,113,0.35);
    border-radius: 10px; padding: 10px 14px;
    font-size: 0.85rem; color: #FCA5A5; margin: 6px 0;
}

.hist-item {
    padding: 10px 12px; border-radius: 8px;
    margin-bottom: 4px; font-size: 0.84rem;
    color: var(--text-2); border: 1px solid var(--line);
    background: var(--surface-2);
    display: flex; justify-content: space-between; align-items: center;
}
.hist-ticker { font-weight: 600; color: var(--text); }
.hist-time { font-size: 0.72rem; color: var(--text-3); }

.ticker-chip {
    display: inline-block;
    font-family: var(--mono);
    background: var(--accent-soft);
    border: 1px solid rgba(91,155,255,0.3);
    color: var(--accent-hi);
    padding: 2px 12px; border-radius: 99px;
    font-size: 0.82rem; font-weight: 600;
    margin-left: 10px; vertical-align: middle;
}

/* ---------- empty-state hero ---------- */
.hero-wrap {
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    padding: 72px 20px 28px;
    position: relative; z-index: 5;
    text-align: center;
}
.hero-badge {
    display: inline-flex; align-items: center; gap: 8px;
    font-family: var(--mono);
    font-size: 11.5px; font-weight: 500; color: var(--accent-hi);
    text-transform: uppercase; letter-spacing: 0.07em;
    margin-bottom: 18px;
}
.bdot { width: 7px; height: 7px; border-radius: 50%; background: var(--up); display: inline-block; }
.hero-greeting {
    font-size: clamp(1.8rem, 3.6vw, 2.6rem); font-weight: 700;
    color: var(--text); margin-bottom: 14px;
    letter-spacing: -0.03em; line-height: 1.15; text-align: center;
}
.hero-greeting em { font-style: normal; color: var(--accent-hi); }
.hero-sub {
    font-size: 1rem; color: var(--text-2);
    margin-bottom: 30px; text-align: center; line-height: 1.7; max-width: 560px;
}
.quick-chips { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; margin-top: 16px; }
.quick-chip {
    font-family: var(--mono);
    background: var(--surface); border: 1px solid var(--line);
    color: var(--text-2); border-radius: 99px;
    padding: 4px 14px; font-size: 12px;
}

@media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }

/* ---------- skeuomorphism: brushed steel, glass buttons, recessed screens ---------- */
:root {
    --bg:#1D222A; --surface:#2F3642; --surface-2:#363D4A; --line:#10141A; --line-2:#4A5260;
    --panel:linear-gradient(180deg,#3E4652 0%,#313845 55%,#2A303B 100%);
    --metal-btn:linear-gradient(180deg,#566070 0%,#3C4452 48%,#323946 52%,#3B4351 100%);
    --screen:linear-gradient(180deg,#0C1015 0%,#151A21 100%);
    --glass:linear-gradient(180deg,#A6CDFF 0%,#5B9BFF 46%,#2F6BD1 54%,#4E8AE6 100%);
    --bevel:inset 0 1px 0 rgba(255,255,255,.17),inset 0 -1px 0 rgba(0,0,0,.45),0 8px 18px rgba(0,0,0,.5);
    --bevel-sm:inset 0 1px 0 rgba(255,255,255,.2),inset 0 -1px 0 rgba(0,0,0,.45),0 3px 6px rgba(0,0,0,.5);
    --well:inset 0 3px 8px rgba(0,0,0,.85),inset 0 -1px 0 rgba(255,255,255,.05),0 1px 0 rgba(255,255,255,.08);
    --grain:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix values='0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 .075 0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
    --brushed:repeating-linear-gradient(90deg,rgba(255,255,255,.022) 0 1px,transparent 1px 4px);
}
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"], .stApp {
    background: var(--grain), var(--brushed), linear-gradient(180deg,#232932,#171B21) !important;
    background-attachment: fixed !important;
}
h1, h2, h3 { text-shadow: 0 1px 0 rgba(255,255,255,.07), 0 -1px 1px rgba(0,0,0,.65); }
[data-testid="stSidebar"] {
    background: var(--brushed), linear-gradient(180deg,#3A424E,#2A303A) !important;
    border-right: 1px solid #0A0D11 !important;
    box-shadow: inset -1px 0 0 rgba(255,255,255,.1), 6px 0 16px rgba(0,0,0,.5) !important;
}
.stButton > button,
[data-testid="stSidebar"] .stButton > button,
[data-testid="stSidebar"] [data-testid="stPageLink"] a {
    background: var(--metal-btn) !important;
    border: 1px solid #11151A !important;
    box-shadow: var(--bevel-sm) !important;
    text-shadow: 0 -1px 0 rgba(0,0,0,.65) !important;
}
.stButton > button:hover,
[data-testid="stSidebar"] .stButton > button:hover,
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
    background: var(--metal-btn) !important;
    border-color: #11151A !important;
    filter: brightness(1.12);
}
.stButton > button:active,
[data-testid="stSidebar"] .stButton > button:active {
    background: linear-gradient(180deg,#2E3541,#3A4250) !important;
    box-shadow: inset 0 3px 7px rgba(0,0,0,.7) !important;
    transform: translateY(1px) !important; filter: none;
}
.stButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"] {
    background: var(--glass) !important;
    border: 1px solid #1A4590 !important;
    color: var(--accent-ink) !important;
    text-shadow: 0 1px 0 rgba(255,255,255,.45) !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.65), inset 0 -2px 3px rgba(10,40,100,.35), 0 3px 7px rgba(0,0,0,.55), 0 0 0 1px rgba(0,0,0,.4) !important;
}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="stBaseButton-primary"]:hover { background: var(--glass) !important; border-color: #1A4590 !important; filter: brightness(1.09); transform: none; }
.stButton > button[kind="primary"]:active,
.stButton > button[data-testid="stBaseButton-primary"]:active {
    background: linear-gradient(180deg,#2F6BD1 0%,#3F7CE0 50%,#5B9BFF 100%) !important;
    box-shadow: inset 0 3px 7px rgba(0,10,40,.65), 0 0 0 1px rgba(0,0,0,.4) !important;
}
.stTextInput input { background: transparent !important; border: 0 !important; box-shadow: none !important; }
.stTextInput input:focus { box-shadow: none !important; }
.stTextInput [data-baseweb="base-input"],
.stTextInput [data-baseweb="input"],
[data-baseweb="select"] > div {
    background: var(--screen) !important;
    border: 1px solid #07090C !important;
    border-radius: 10px !important;
    box-shadow: var(--well) !important;
}
.stTextInput [data-baseweb="base-input"]:focus-within,
.stTextInput [data-baseweb="input"]:focus-within,
[data-baseweb="select"] > div:focus-within { box-shadow: var(--well), 0 0 0 2px var(--accent) !important; }
[data-baseweb="popover"] ul, [data-baseweb="menu"] { background: var(--panel) !important; border: 1px solid #0E1217 !important; box-shadow: 0 10px 24px rgba(0,0,0,.65) !important; }
.semi-card, .reasoning-card, .bot-bubble, .hist-item {
    background: var(--panel) !important;
    border: 1px solid #0E1217 !important;
    box-shadow: var(--bevel);
}
.semi-card { border-radius: 12px; }
.semi-card:hover { filter: brightness(1.07); }
.semi-card.hover-expand .hover-tooltip { background: var(--panel); border: 1px solid #0E1217; box-shadow: 0 12px 28px rgba(0,0,0,.7), inset 0 1px 0 rgba(255,255,255,.18); }
.metric-card {
    background: var(--screen) !important;
    border: 1px solid #07090C !important;
    box-shadow: var(--well);
}
.metric-num-up { text-shadow: 0 0 12px rgba(52,211,153,.55); }
.metric-num-dn { text-shadow: 0 0 12px rgba(248,113,113,.5); }
.reasoning-card { border-left: 3px solid var(--accent) !important; }
.user-bubble, .semibot-bubble-user {
    background: linear-gradient(180deg,#B2D3FF 0%,#6FA6FF 50%,#5B9BFF 100%);
    border: 1px solid #1A4590; color: #06101F;
    text-shadow: 0 1px 0 rgba(255,255,255,.4);
    box-shadow: inset 0 1px 0 rgba(255,255,255,.7), 0 3px 6px rgba(0,0,0,.5);
}
.sec-label::after { height: 2px; background: rgba(0,0,0,.6); box-shadow: 0 1px 0 rgba(255,255,255,.08); }
.bar-track { height: 12px; padding: 2px; background: var(--screen); border: 1px solid #07090C; box-shadow: var(--well); }
.bar-up, .bar-dn { background-image: linear-gradient(180deg,rgba(255,255,255,.4),rgba(255,255,255,0) 55%); }
.disclaimer, .val-error { border: 1px solid #07090C; background: var(--screen); box-shadow: var(--well); }
.ticker-chip { background: var(--screen); border: 1px solid #07090C; box-shadow: inset 0 2px 4px rgba(0,0,0,.7); }
.ticker-wrap { background: var(--screen) !important; border-top: 1px solid #000 !important; box-shadow: inset 0 3px 8px rgba(0,0,0,.8); }
</style>
""", unsafe_allow_html=True)



VALID_TICKERS = {
    "MU", "SNDK",
    "NVDA", "AMD", "INTC", "QCOM", "AVGO", "MRVL", "ARM",
    "ASML", "AMAT", "LRCX", "KLAC", "ONTO", "ACMR", "MKSI",
    "TXN", "ADI", "MCHP", "MPWR", "SWKS", "QRVO", "SLAB", "SMTC",
    "TSM", "GFS", "UMC",
    "ON", "STM", "NXPI", "ALGM", "DIOD",
    "ALAB", "FORM", "RMBS",
    "CRUS", "SITM", "MTSI",
    "000660.KS", "005930.KS",
    "2308.TW", "2454.TW", "3711.TW",
    "6723.T", "6857.T", "8035.T", "285A.T",
    "IFX.DE", "ASMI.AS", "BE.NA",
}

COMPANY_NAME_MAP = {
    "micron": "MU", "micron technology": "MU",
    "sandisk": "SNDK", "sandisk corporation": "SNDK",
    "nvidia": "NVDA", "nvidia corporation": "NVDA",
    "amd": "AMD", "advanced micro devices": "AMD",
    "intel": "INTC", "intel corporation": "INTC",
    "qualcomm": "QCOM", "qualcomm incorporated": "QCOM",
    "broadcom": "AVGO", "broadcom inc": "AVGO",
    "marvell": "MRVL", "marvell technology": "MRVL",
    "arm": "ARM", "arm holdings": "ARM",
    "asml": "ASML", "asml holding": "ASML",
    "applied materials": "AMAT",
    "lam research": "LRCX", "lam research corporation": "LRCX",
    "kla": "KLAC", "kla corporation": "KLAC",
    "onto innovation": "ONTO",
    "acm research": "ACMR",
    "mks": "MKSI", "mks instruments": "MKSI",
    "texas instruments": "TXN",
    "analog devices": "ADI",
    "microchip": "MCHP", "microchip technology": "MCHP",
    "monolithic power": "MPWR", "monolithic power systems": "MPWR",
    "skyworks": "SWKS", "skyworks solutions": "SWKS",
    "qorvo": "QRVO",
    "silicon labs": "SLAB", "silicon laboratories": "SLAB",
    "semtech": "SMTC", "semtech corporation": "SMTC",
    "tsmc": "TSM", "taiwan semiconductor": "TSM", "taiwan semiconductor manufacturing": "TSM",
    "globalfoundries": "GFS",
    "umc": "UMC", "united microelectronics": "UMC",
    "on semiconductor": "ON", "onsemi": "ON",
    "stmicroelectronics": "STM", "st microelectronics": "STM",
    "nxp": "NXPI", "nxp semiconductors": "NXPI",
    "allegro microsystems": "ALGM", "allegro": "ALGM",
    "diodes incorporated": "DIOD", "diodes": "DIOD",
    "astera labs": "ALAB",
    "formfactor": "FORM",
    "rambus": "RMBS",
    "cirrus logic": "CRUS",
    "sitime": "SITM",
    "macom": "MTSI", "macom technology": "MTSI",
    "sk hynix": "000660.KS", "hynix": "000660.KS", "sk hynix inc": "000660.KS",
    "samsung": "005930.KS", "samsung electronics": "005930.KS",
    "delta electronics": "2308.TW",
    "mediatek": "2454.TW",
    "ase technology": "3711.TW", "ase group": "3711.TW",
    "renesas": "6723.T", "renesas electronics": "6723.T",
    "advantest": "6857.T", "advantest corporation": "6857.T",
    "tokyo electron": "8035.T",
    "kioxia": "285A.T", "toshiba memory": "285A.T",
    "infineon": "IFX.DE", "infineon technologies": "IFX.DE",
    "asm international": "ASMI.AS", "asmi": "ASMI.AS",
    "be semiconductor": "BE.NA", "besi": "BE.NA",
}

TICKER_TO_NAME = {}
for _name, _tick in COMPANY_NAME_MAP.items():
    if _tick not in TICKER_TO_NAME or len(_name) > len(TICKER_TO_NAME[_tick]):
        TICKER_TO_NAME[_tick] = _name

def format_ticker_option(name, tick):
    clean_ticker = tick.split(".")[0]
    if name.replace(" ", "").upper() == clean_ticker.upper():
        return f"{clean_ticker} ({tick})"
    return f"{name.title()} ({tick})"

def build_ticker_options():
    named_options = []
    bare_options = []
    seen = set()
    for name, tick in COMPANY_NAME_MAP.items():
        if tick not in seen:
            named_options.append(format_ticker_option(name, tick))
            seen.add(tick)
    for tick in sorted(VALID_TICKERS):
        if tick not in seen:
            bare_options.append(f"({tick})")
            seen.add(tick)
    return sorted(named_options) + sorted(bare_options)

TICKER_OPTIONS = build_ticker_options()

def build_bubble_context():
    """Richer system prompt for the floating chat bubble when an analysis
    (single-ticker or compare) already exists in this session; otherwise
    returns None so the bubble falls back to its generic identity prompt."""
    if st.session_state.get("result") and st.session_state.get("ticker"):
        result = st.session_state.result
        ticker = st.session_state.ticker
        p = parse_result(result)
        historical_context = get_historical_context(ticker)
        live_prices = _live_price_block()
        return f"""You are analyzing {ticker} stock. Here is the complete 18-factor analysis:

LONG_TERM_MEMORY: {historical_context}
The above line lists ONLY past UP% values for {ticker} with timestamps, most recent first - nothing else.

PREDICTION: UP {p['up_prob']}% / DOWN {p['down_prob']}% (Confidence: {p['confidence']})
REASONING: {p['reasoning']}
BULLISH FACTORS: {', '.join(p['bullish'])}
BEARISH FACTORS: {', '.join(p['bearish'])}
CPI: {result.get('cpi','N/A')} | PPI: {result.get('ppi','N/A')} | Fed Rate: {result.get('fed_rate','N/A')} | USD Index: {result.get('usd_index','N/A')}
P/E Ratio: {result.get('pe_ratio','N/A')} | Market Cap: {result.get('market_cap','N/A')} | Earnings: {result.get('earnings_guidance','N/A')} | Insider: {result.get('insider_selling','N/A')}
Sector Rally: {result.get('sector_rally','N/A')} | Technical: {result.get('technical_signal','N/A')} | Analyst: {result.get('analyst_ratings','N/A')}
Geopolitics: {result.get('geopolitics','N/A')} | Supply Chain: {result.get('supply_chain','N/A')}

IDENTITY (HIGHEST PRIORITY): You are SemiBot, an 18-factor agentic RAG system for semiconductor equity analysis, created by Raj Tejpal Khatik, an MSc Applied AI student at the University of Warwick, targeting ACM FinNLP.
- If asked "who are you": say "I am SemiBot - an AI-powered semiconductor equity analyser built on 18 causal factors. Created by Raj Tejpal Khatik at the University of Warwick."
- If asked "who created you" or "who is Raj" or "who made you": say "I was created by Raj Tejpal Khatik, an MSc Applied AI student at the University of Warwick."
- Never say you are ChatGPT, Claude, or any other AI.

TOPIC RULES: Answer questions about companies, stocks, markets, finance, economics, business, or technology freely and helpfully, including CEOs, executives, share prices, company history, products, competitors, or comparisons for {ticker} or ANY other company.
Only refuse if the question has absolutely nothing to do with business, finance, companies, or technology, such as asking for a recipe, a poem, medical advice, or help with unrelated homework. If there is any plausible connection to business/finance/tech, just answer it.
Refusal message (use only for clearly unrelated requests): "I'm focused on semiconductor equity analysis and can't help with that. Feel free to ask me about {ticker}, market factors, or the analysis above!"
{live_prices}"""
    if st.session_state.get("compare_results"):
        tickers_list = list(st.session_state.compare_results.keys())
        combined_summary = ""
        for t in tickers_list:
            r = st.session_state.compare_results[t]
            p = parse_result(r)
            hist_context = get_historical_context(t)
            name = TICKER_TO_NAME.get(t, t)
            combined_summary += f"""
--- {name} ---
PREDICTION: UP {p['up_prob']}% / DOWN {p['down_prob']}% (Confidence: {p['confidence']})
REASONING: {p['reasoning']}
CPI: {r.get('cpi','N/A')} | PPI: {r.get('ppi','N/A')} | Fed Rate: {r.get('fed_rate','N/A')} | USD Index: {r.get('usd_index','N/A')}
LONG_TERM_MEMORY for {name}: {hist_context}
"""
        live_prices = _live_price_block()
        return f"""You are SemiBot, comparing {len(tickers_list)} semiconductor tickers side by side: {', '.join(TICKER_TO_NAME.get(t, t) for t in tickers_list)}.

Here is the full 18-factor analysis for each:
{combined_summary}

Answer the user's question by comparing across these tickers where relevant. Reference specific tickers by name when making comparisons.

IDENTITY (HIGHEST PRIORITY): You are SemiBot, an 18-factor agentic RAG system for semiconductor equity analysis, created by Raj Tejpal Khatik, an MSc Applied AI student at the University of Warwick, targeting ACM FinNLP.
- If asked "who are you" or "who is Raj" or "who made you" or "who created you" or "who is Raj Tejpal Khatik": say "I am SemiBot, an AI-powered semiconductor equity analyser. I was created by Raj Tejpal Khatik, an MSc Applied AI student at the University of Warwick."
- Never say you are ChatGPT, Claude, or any other AI.

TOPIC RULES:
- If the user types just a company name or ticker alone, treat it as "tell me about this company" and answer with what you know about it - this is always on-topic, never refuse it.
- Answer questions about CEOs, executives, share prices, company history, products, competitors, or comparisons for any company freely.
- Only use the refusal message below if the question is truly unrelated to business/finance/companies/technology, such as asking for a recipe, a poem, or medical advice.
Refusal message (use ONLY for clearly unrelated requests like recipes or medical advice): "I'm focused on semiconductor equity analysis and can't help with that. Feel free to ask me about these tickers, market factors, or the comparison above!"
{live_prices}"""
    return None

def extract_ticker_from_option(option_str: str):
    if "(" in option_str and option_str.endswith(")"):
        return option_str.rsplit("(", 1)[1].rstrip(")").strip()
    return option_str.strip()

def validate_ticker(user_input: str):
    if not user_input or not user_input.strip():
        return None, "Please enter a ticker symbol or company name."
    input_lower = user_input.strip().lower()
    input_upper = user_input.strip().upper()
    if input_lower in COMPANY_NAME_MAP:
        return COMPANY_NAME_MAP[input_lower], None
    if not re.match(r'^[A-Za-z0-9.\-]{1,12}$', input_upper):
        return None, f"'{user_input}' is not a valid input. Please enter a ticker like MU, NVDA, AMD or a company name like Micron, NVIDIA."
    if input_upper not in VALID_TICKERS:
        return None, f"'{input_upper}' is not a recognised semiconductor ticker. SemiBot supports: MU, NVDA, AMD, INTC, TSM, ASML, QCOM, TXN, AMAT, LRCX, AVGO, MRVL, ON, NXPI, ADI, MCHP, KLAC, SWKS, MPWR."
    return input_upper, None

if "visit_logged" not in st.session_state:
    log_event("visit", detail="analysis page")
    st.session_state.visit_logged = True

render_chat_bubble(get_system_prompt=build_bubble_context)

if "history" not in st.session_state:
    st.session_state.history = load_history()
if "result" not in st.session_state:
    st.session_state.result = None
if "ticker" not in st.session_state:
    st.session_state.ticker = None
if "followup_history" not in st.session_state:
    st.session_state.followup_history = []
if "last_ticker" not in st.session_state:
    st.session_state.last_ticker = None
if "current_history_id" not in st.session_state:
    st.session_state.current_history_id = None
if "thread_id" not in st.session_state:
    st.session_state.thread_id = f"session_{int(time.time())}"
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "single"
if "ticker_count" not in st.session_state:
    st.session_state.ticker_count = None
if "compare_results" not in st.session_state:
    st.session_state.compare_results = {}
if "compare_sessions_list" not in st.session_state:
    st.session_state.compare_sessions_list = load_compare_sessions()
if "current_compare_session_id" not in st.session_state:
    st.session_state.current_compare_session_id = None
with st.sidebar:
    st.markdown("""
    <div style='display:flex;align-items:center;gap:10px;margin-bottom:4px'>
        <div style='width:32px;height:32px;border-radius:8px;background:rgba(91,155,255,0.12);border:1px solid rgba(91,155,255,0.35);display:flex;align-items:center;justify-content:center'><svg viewBox='0 0 24 24' width='18' height='18' fill='none' stroke='#8BB8FF' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'><rect x='6' y='6' width='12' height='12' rx='2'/><path d='M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3'/></svg></div>
        <span style='font-family:Inter,sans-serif;font-size:16px;font-weight:700;color:#EDF0F5'>SemiBot</span>
    </div>
    <div style='font-size:0.72rem;color:#9AA6B8;margin-bottom:18px'>18-Factor Agentic RAG</div>
    """, unsafe_allow_html=True)

    # PATH FIX 5: Use st.page_link for same-tab navigation to Home page
    st.page_link("app.py", label="Home", use_container_width=True)
    if st.button("+ New Analysis", use_container_width=True):
        st.session_state.result = None
        st.session_state.ticker = None
        st.session_state.followup_history = []
        st.session_state.current_history_id = None
        st.rerun()

    st.markdown("<hr style='border-color:#3A4658;margin:14px 0'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.65rem;color:#9AA6B8;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:10px'>HISTORY</div>", unsafe_allow_html=True)

    if st.session_state.history:
        for item in st.session_state.history[:10]:
            try:
                up_val = float(item.get("up", "50%").replace("%", "").strip())
            except:
                up_val = 50
            label = f"{item['ticker']}  {item.get('up','?')}  {item['time']}"
            if st.button(label, key=f"hist_{item['id']}", use_container_width=True):
                ticker_r, result_r, followup_r = load_history_detail(item['id'])
                if result_r is not None:
                    st.session_state.result = result_r
                    st.session_state.ticker = ticker_r
                    st.session_state.followup_history = followup_r
                    st.session_state.current_history_id = item['id']
                    st.session_state.active_tab = "single"
                    st.rerun()

    st.markdown("<hr style='border-color:#3A4658;margin:14px 0'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.65rem;color:#9AA6B8;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:10px'>COMPARISONS</div>", unsafe_allow_html=True)

    if st.session_state.compare_sessions_list:
        for csession in st.session_state.compare_sessions_list[:10]:
            tickers_preview = csession["tickers_csv"].split(",")
            label = f"{len(tickers_preview)} tickers - {csession['time']}"
            if st.button(label, key=f"cmp_hist_{csession['id']}", use_container_width=True):
                tickers_r, results_r, followup_r = load_compare_session_detail(csession['id'])
                if results_r is not None:
                    st.session_state.compare_results = results_r
                    st.session_state.compare_followup_history = followup_r
                    st.session_state.current_compare_session_id = csession['id']
                    st.session_state.ticker_count = len(tickers_r)
                    st.session_state.active_tab = "compare"
                    st.rerun()

if st.session_state.result is None:
    tcol1, tcol2 = st.columns(2)
    with tcol1:
        if st.button("Single ticker", use_container_width=True,
                      type="primary" if st.session_state.active_tab == "single" else "secondary"):
            st.session_state.active_tab = "single"
            st.rerun()
    with tcol2:
        if st.button("Compare tickers", use_container_width=True,
                      type="primary" if st.session_state.active_tab == "compare" else "secondary"):
            st.session_state.active_tab = "compare"
            st.rerun()

    if st.session_state.active_tab == "compare":
        st.markdown("<div style='padding:16px 0'>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.75rem;color:#A4AFC0;margin-bottom:10px'>How many tickers do you want to compare?</div>", unsafe_allow_html=True)

        count_cols = st.columns(5)
        for i, c in enumerate(count_cols):
            with c:
                if st.button(str(i + 1), use_container_width=True, key=f"count_btn_{i+1}",
                              type="primary" if st.session_state.ticker_count == (i + 1) else "secondary"):
                    st.session_state.ticker_count = i + 1
                    st.rerun()

        if st.session_state.ticker_count:
            selected_options = []
            for i in range(st.session_state.ticker_count):
                opt = st.selectbox(
                    f"Ticker {i+1}",
                    options=[""] + TICKER_OPTIONS,
                    key=f"cmp_ticker_{i}",
                )
                selected_options.append(opt)

            compare_go = st.button("Compare ->", type="primary")

            if compare_go:
                chosen_raw = [o for o in selected_options if o.strip()]
                seen_options = set()
                chosen = []
                had_duplicates = False
                for o in chosen_raw:
                    if o in seen_options:
                        had_duplicates = True
                        continue
                    seen_options.add(o)
                    chosen.append(o)

                if had_duplicates:
                    st.markdown("<div class='val-error'>Warning: Duplicate ticker selections were removed - each ticker can only be compared once.</div>", unsafe_allow_html=True)

                if not chosen:
                    st.markdown("<div class='val-error'>Warning: Please select at least one ticker.</div>", unsafe_allow_html=True)
                else:
                    log_event("search", detail=f"Compared tickers: {', '.join(chosen)}")
                    from graph.nodes import resolve_ticker
                    compare_results = {}
                    progress = st.progress(0, text="Starting comparison...")
                    
                    from concurrent.futures import ThreadPoolExecutor, as_completed

                    resolved_final_tickers = []
                    for opt in chosen:
                        raw_ticker = extract_ticker_from_option(opt)
                        resolved_ticker, error_msg = validate_ticker(raw_ticker)
                        if error_msg:
                            st.markdown(f"<div class='val-error'>Warning: '{raw_ticker}' skipped - {error_msg}</div>", unsafe_allow_html=True)
                            continue
                        final_t = resolve_ticker(resolved_ticker)
                        resolved_final_tickers.append(final_t)

                    def run_single_analysis(ticker_symbol):
                        print(f"[PARALLEL CHECK] {ticker_symbol} STARTED at {time.time():.2f}", flush=True)
                        thread_id = f"compare_{int(time.time())}_{ticker_symbol}"
                        thread_local_app = build_graph()
                        merged_result = {}
                        for chunk in thread_local_app.stream(
                            {"ticker": ticker_symbol},
                            config={"configurable": {"thread_id": thread_id}},
                            stream_mode="updates"
                        ):
                            for node_name, node_data in chunk.items():
                                for k, v in node_data.items():
                                    if v:
                                        merged_result[k] = v
                        return ticker_symbol, merged_result

                    completed = 0
                    total = len(resolved_final_tickers)
                    with ThreadPoolExecutor(max_workers=total if total > 0 else 1) as executor:
                        futures = {executor.submit(run_single_analysis, t): t for t in resolved_final_tickers}
                        for future in as_completed(futures):
                            ticker_symbol = futures[future]
                            try:
                                t, r = future.result()
                                compare_results[t] = r
                            except Exception as e:
                                st.markdown(f"<div class='val-error'>Warning: {ticker_symbol} failed - {str(e)}</div>", unsafe_allow_html=True)
                            completed += 1
                            progress.progress(int((completed/total)*100), text=f"{completed}/{total} tickers analysed")
                    progress.empty()
                    st.session_state.compare_results = compare_results
                    st.session_state.compare_followup_history = []

                    if compare_results:
                        for _t, _r in compare_results.items():
                            _p = parse_result(_r)
                            _up_str = f"{_p['up_prob']}%"
                            save_history(_t, _up_str, uk_time_str(), _r, [])

                        save_compare_session(
                            list(compare_results.keys()),
                            uk_time_str(),
                            compare_results,
                            []
                        )
                        st.session_state.compare_sessions_list = load_compare_sessions()
                        st.session_state.history = load_history()
                        if st.session_state.compare_sessions_list:
                            st.session_state.current_compare_session_id = st.session_state.compare_sessions_list[0]["id"]

        if st.session_state.compare_results:
            st.markdown("<hr style='border-color:#3A4658;margin:20px 0'>", unsafe_allow_html=True)
            tickers_list = list(st.session_state.compare_results.keys())

            ranked = sorted(tickers_list, key=lambda t: parse_result(st.session_state.compare_results[t])["up_prob"], reverse=True)

            def display_name(t):
                name = TICKER_TO_NAME.get(t)
                if not name:
                    return t
                clean_ticker = t.split(".")[0]
                if name.replace(" ", "").upper() == clean_ticker.upper():
                    return f"{clean_ticker} ({t})"
                return f"{name.title()} ({t})"

            st.markdown("<div class='sec-label' style='font-size:0.7rem'>Priority ranking (highest upside first)</div>", unsafe_allow_html=True)
            rank_html = ""
            for i, t in enumerate(ranked):
                p = parse_result(st.session_state.compare_results[t])
                rank_color = "#34D399" if p["up_prob"] >= p["down_prob"] else "#F87171"
                rank_html += f"<div class='semi-card' style='display:flex;justify-content:space-between;align-items:center;padding:8px 14px'><span style='font-size:0.8rem;color:#EDF0F5'>{i+1}. {display_name(t)}</span><span style='font-family:Inter,sans-serif;font-weight:700;color:{rank_color}'>{p['up_prob']}% / {p['down_prob']}%</span></div>"
            st.markdown(rank_html, unsafe_allow_html=True)

            st.markdown("<hr style='border-color:#3A4658;margin:20px 0'>", unsafe_allow_html=True)

            cols = st.columns(len(tickers_list))
            factor_groups = [
                ("Macroeconomic", [("CPI","cpi"),("PPI","ppi"),("Fed Rate","fed_rate"),("USD Index","usd_index")]),
                ("Fundamental", [("P/E Ratio","pe_ratio"),("Market Cap","market_cap"),("Earnings Guidance","earnings_guidance"),("Insider Selling","insider_selling")]),
                ("Market Intelligence", [("Sector Rally","sector_rally"),("Technical Signal","technical_signal"),("Analyst Ratings","analyst_ratings"),("Sell-the-News","sell_the_news")]),
                ("External Signals", [("Geopolitics","geopolitics"),("Supply Chain","supply_chain"),("News Sentiment","news_sentiment"),("Capital Rotation","capital_rotation"),("Competitor Contagion","competitor_contagion"),("Beta","beta")]),
            ]
            for col, t in zip(cols, tickers_list):
                with col:
                    r = st.session_state.compare_results[t]
                    parsed = parse_result(r)
                    scores = r.get("scores", {})
                    st.markdown(f"<div style='font-family:Inter,sans-serif;font-size:0.9rem;font-weight:700;color:#EDF0F5;margin-bottom:8px' title='{display_name(t)}'>{display_name(t)}</div>", unsafe_allow_html=True)
                    up_color = "#34D399" if parsed["up_prob"] >= parsed["down_prob"] else "#F87171"
                    st.markdown(f"""
                    <div class='metric-card' style='margin-bottom:10px'>
                        <div class='metric-lbl'>Upside / Downside</div>
                        <div style='font-family:Inter,sans-serif;font-size:1.4rem;font-weight:700;color:{up_color}'>{parsed['up_prob']}% / {parsed['down_prob']}%</div>
                        <div style='font-size:0.68rem;color:#9AA6B8;margin-top:4px'>Confidence: {parsed['confidence']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    for group_label, pairs in factor_groups:
                        st.markdown(f"<div class='sec-label' style='font-size:0.6rem'>{group_label}</div>", unsafe_allow_html=True)
                        for label, key in pairs:
                            raw_val = str(r.get(key, "N/A")).strip()
                            if not raw_val:
                                raw_val = "N/A"
                            score_val = scores.get(key)
                            sentiment_label = "Bullish" if (score_val or 0) > 0 else ("Bearish" if (score_val or 0) < 0 else "Neutral")
                            tooltip_body = smart_truncate(raw_val, limit=1200).replace("'", "&#39;")
                            full_val = f"{label}: {tooltip_body}"
                            st.markdown(f"<div class='semi-card hover-expand' style='padding:8px 10px'><div class='card-key' style='font-size:0.58rem'>{label}</div><div class='card-val' style='font-size:0.7rem'>{sentiment_label}</div>{score_badge(key, scores)}<div class='hover-tooltip'>{full_val}</div></div>", unsafe_allow_html=True)

            st.markdown("<hr style='border-color:#3A4658;margin:24px 0'>", unsafe_allow_html=True)
            st.markdown("<div style='font-family:Inter,sans-serif;font-size:0.95rem;font-weight:600;color:#EDF0F5;margin-bottom:6px'>Ask a follow-up question</div>", unsafe_allow_html=True)
            st.markdown("<div style='font-size:0.75rem;color:#A4AFC0;margin-bottom:12px'>Ask about any or all of the compared tickers - e.g. \"which has the strongest fundamentals?\" or \"compare their supply chain risk\"</div>", unsafe_allow_html=True)

            if "compare_followup_history" not in st.session_state:
                st.session_state.compare_followup_history = []

            for msg in st.session_state.compare_followup_history:
                if msg["role"] == "user":
                    st.markdown(f"<div class='user-bubble'>{msg['content']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='bot-bubble'><div style='font-size:0.65rem;color:#8BB8FF;font-weight:600;margin-bottom:4px'>SEMIBOT</div>{msg['content']}</div>", unsafe_allow_html=True)

            if "compare_input_counter" not in st.session_state:
                st.session_state.compare_input_counter = 0

            cfq1, cfq2 = st.columns([5, 1])
            with cfq1:
                compare_followup_q = st.text_input("", placeholder="e.g. Which ticker has the best risk/reward right now?", label_visibility="collapsed", key=f"compare_followup_input_{st.session_state.compare_input_counter}")
            with cfq2:
                compare_ask_button = st.button("Ask ->", use_container_width=True, key="compare_ask_btn", type="primary")

            if compare_ask_button and compare_followup_q:
                combined_summary = ""
                for t in tickers_list:
                    r = st.session_state.compare_results[t]
                    p = parse_result(r)
                    hist_context = get_historical_context(t)
                    combined_summary += f"""
--- {display_name(t)} ---
PREDICTION: UP {p['up_prob']}% / DOWN {p['down_prob']}% (Confidence: {p['confidence']})
REASONING: {p['reasoning']}
CPI: {r.get('cpi','N/A')} | PPI: {r.get('ppi','N/A')} | Fed Rate: {r.get('fed_rate','N/A')} | USD Index: {r.get('usd_index','N/A')}
P/E Ratio: {r.get('pe_ratio','N/A')} | Market Cap: {r.get('market_cap','N/A')} | Earnings: {r.get('earnings_guidance','N/A')} | Insider: {r.get('insider_selling','N/A')}
Sector Rally: {r.get('sector_rally','N/A')} | Technical: {r.get('technical_signal','N/A')} | Analyst: {r.get('analyst_ratings','N/A')}
Geopolitics: {r.get('geopolitics','N/A')} | Supply Chain: {r.get('supply_chain','N/A')}
LONG_TERM_MEMORY for {display_name(t)}: {hist_context}
"""
                context = f"""You are SemiBot, comparing {len(tickers_list)} semiconductor tickers side by side: {', '.join(display_name(t) for t in tickers_list)}.

Here is the full 18-factor analysis for each:
{combined_summary}

Answer the user's question by comparing across these tickers where relevant. Reference specific tickers by name when making comparisons.

IDENTITY (HIGHEST PRIORITY): You are SemiBot, an 18-factor agentic RAG system for semiconductor equity analysis, created by Raj Tejpal Khatik, an MSc Applied AI student at the University of Warwick, targeting ACM FinNLP.
- If asked "who are you" or "who is Raj" or "who made you" or "who created you" or "who is Raj Tejpal Khatik": say "I am SemiBot, an AI-powered semiconductor equity analyser. I was created by Raj Tejpal Khatik, an MSc Applied AI student at the University of Warwick."
- Never say you are ChatGPT, Claude, or any other AI.

TOPIC RULES:
- If the user types just a company name or ticker alone (examples: "micron", "mu", "nvidia", "intel"), treat it as "tell me about this company" and answer with what you know about it - this is always on-topic, never refuse it.
- If asked "what does X do" or "what is X" for any company (in this comparison or not), answer normally with a business description.
- Answer questions about CEOs, executives, share prices, company history, products, competitors, or comparisons for any company freely.
- A "what is the current price of X" question is ALWAYS on-topic and answerable - use the LIVE PRICES data below if the ticker is listed there. This is NOT a refusal-worthy request under any circumstance.
- Only use the refusal message below if the question is truly unrelated to business/finance/companies/technology, such as asking for a recipe, a poem, or medical advice.
Refusal message (use ONLY for clearly unrelated requests like recipes or medical advice): "I'm focused on semiconductor equity analysis and can't help with that. Feel free to ask me about these tickers, market factors, or the comparison above!"
{_live_price_block()}"""
                st.session_state.compare_followup_history.append({"role": "user", "content": compare_followup_q})
                from graph.nodes import llm
                from langchain_core.messages import SystemMessage, HumanMessage
                messages = [SystemMessage(content=context), HumanMessage(content=compare_followup_q)]
                with st.chat_message("assistant"):
                    try:
                        response_text = st.write_stream(chunk.content for chunk in llm.stream(messages) if hasattr(chunk, "content") and chunk.content)
                    except GeneratorExit:
                        response_text = ""
                st.session_state.compare_followup_history.append({"role": "assistant", "content": response_text})
                log_event("chat", question=compare_followup_q, reply=response_text)
                st.session_state.compare_input_counter += 1
                if st.session_state.current_compare_session_id:
                    update_compare_followup(st.session_state.current_compare_session_id, st.session_state.compare_followup_history)
                st.rerun()

            if st.button("Clear comparison"):
                st.session_state.compare_results = {}
                st.session_state.ticker_count = None
                st.session_state.compare_followup_history = []
                st.session_state.current_compare_session_id = None
                st.session_state.compare_followup_history = []
                st.rerun()

        st.markdown("<hr style='border-color:#3A4658;margin:24px 0'>", unsafe_allow_html=True)
        st.markdown("<div style='font-family:Inter,sans-serif;font-size:0.95rem;font-weight:600;color:#EDF0F5;margin-bottom:12px'>Email Summary</div>", unsafe_allow_html=True)

        cem1, cem2 = st.columns([4, 1])
        with cem1:
            compare_user_email = st.text_input("", placeholder="Enter your email to receive comparison summary...", label_visibility="collapsed", key="compare_email_input")
        with cem2:
            compare_send_button = st.button("Send", use_container_width=True, key="compare_send_email_btn", type="primary")

        if compare_send_button and compare_user_email:
            try:
                sections = []
                for t in tickers_list:
                    r = st.session_state.compare_results[t]
                    p = parse_result(r)
                    bull_text = "\n".join([f"  + {b}" for b in p['bullish'][:3]])
                    bear_text = "\n".join([f"  - {b}" for b in p['bearish'][:3]])
                    sections.append(f"""
{display_name(t)}
{'-' * 40}
UP: {p['up_prob']}% | DOWN: {p['down_prob']}% | Confidence: {p['confidence']}
BULLISH:
{bull_text}
BEARISH:
{bear_text}
REASONING: {p['reasoning']}
""")

                compare_email_body = f"""SEMICONDUCTOR MULTI-TICKER COMPARISON REPORT
=====================================
Tickers: {', '.join(tickers_list)} | Date: {time.strftime("%d %B %Y, %H:%M")}
Generated by: SemiBot - 18-Factor Agentic RAG System
University of Warwick MSc Applied AI Research

{"".join(sections)}

DISCLAIMER: AI research tool only. Not financial advice.
SemiBot v1.0 | University of Warwick | MSc Applied AI | ACM FinNLP
"""
                sender_email = os.getenv("SENDER_EMAIL")
                sender_password = os.getenv("SENDER_APP_PASSWORD")
                msg = MIMEMultipart()
                msg['From'] = sender_email
                msg['To'] = compare_user_email
                msg['Subject'] = f"SemiBot Comparison - {len(tickers_list)} tickers - {time.strftime('%d %b %Y')}"
                msg.attach(MIMEText(compare_email_body, 'plain'))
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, compare_user_email, msg.as_string())
                server.quit()
                st.success(f"Comparison report sent to {compare_user_email}")
            except Exception as e:
                st.error(f"Email failed: {str(e)}")
        elif compare_send_button and not compare_user_email:
            st.markdown("<div class='val-error'>Warning: Please enter your email address.</div>", unsafe_allow_html=True)

        st.markdown("""
        <div class='disclaimer'>
            Warning: This analysis is generated by an AI research tool for informational and academic purposes only.
            It does NOT constitute financial advice. Always consult a qualified financial advisor.
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        render_ticker_tape()
        st.stop()

if not st.session_state.result:
    st.markdown(f"""
    <div class='hero-wrap'>
        <div class='hero-badge'><span class='bdot'></span> 18-factor causal analysis</div>
        <div class='hero-greeting'>Analyse a <em>semiconductor stock</em></div>
        <div class='hero-sub'>
            An LLM scores 18 causal factors across macro, fundamentals, market signals and supply-chain risk.
            The UP% / DOWN% split is then calculated in Python, not generated by the model.
        </div>
        <div class='quick-chips'>
            <span class='quick-chip'>Macro</span><span class='quick-chip'>Fundamentals</span><span class='quick-chip'>Market intelligence</span><span class='quick-chip'>Supply chain</span><span class='quick-chip'>Geopolitics</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    print(f"[TIMING] Before search bar: {_time.time() - _t0:.2f}s", flush=True)
    col_l, col_m, col_r = st.columns([1, 4, 1])
    with col_m:
        # Deep-link support: pre-select ticker from ?ticker=XXX if present
        _default_idx = 0
        _url_ticker = get_ticker_from_query()
        if _url_ticker and "single_ticker_select" not in st.session_state:
            for _i, _opt in enumerate(["Enter ticker or company name..."] + TICKER_OPTIONS):
                if _url_ticker in _opt.upper():
                    _default_idx = _i
                    break

        selected_option = st.selectbox(
            "Ticker",
            options=["Enter ticker or company name..."] + TICKER_OPTIONS,
            index=_default_idx,
            label_visibility="collapsed",
            key="single_ticker_select"
        )
        ticker_input = extract_ticker_from_option(selected_option) if selected_option != "Enter ticker or company name..." else ""
        # Show company logo preview below the selectbox
        if ticker_input:
            render_ticker_logo(ticker_input, size=52)
        analyse = st.button("Analyse ->", use_container_width=True, type="primary")

else:
    col_h1, col_h2 = st.columns([5, 1])
    with col_h1:
        st.markdown(f"""
        <div style='padding:24px 32px 0'>
            <div style='font-family:Inter,sans-serif;font-size:1.3rem;font-weight:700;color:#EDF0F5;margin-bottom:4px'>
                Factor Analysis <span class='ticker-chip'>{st.session_state.ticker}</span>
            </div>
            <div style='font-size:0.75rem;color:#A4AFC0'>18-Factor Agentic RAG - Real-time APIs - University of Warwick</div>
        </div>
        """, unsafe_allow_html=True)
    with col_h2:
        st.markdown("<div style='padding-top:24px;padding-right:16px'>", unsafe_allow_html=True)
        if st.button("+ New", use_container_width=True):
            st.session_state.result = None
            st.session_state.ticker = None
            st.session_state.followup_history = []
            st.session_state.current_history_id = None
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    ticker_input = ""
    analyse = False

if analyse and ticker_input:
    resolved_ticker, error_msg = validate_ticker(ticker_input)
    if error_msg:
        st.markdown(f"<div class='val-error'>Warning: {error_msg}</div>", unsafe_allow_html=True)
    else:
        log_event("search", detail=f"Single ticker analysed: {resolved_ticker}")
        from graph.nodes import resolve_ticker

        with st.spinner("Resolving ticker..."):
            final_ticker = resolve_ticker(resolved_ticker)

        st.markdown("<div style='padding:0 32px'>", unsafe_allow_html=True)

        progress_bar = st.progress(0, text="Starting analysis...")
        

        ph_macro    = st.empty()
        ph_fund     = st.empty()
        ph_market   = st.empty()
        ph_external = st.empty()

        def make_cards(data, pairs, label):
            html = f"<div class='sec-label'>{label}</div>"
            for lbl, key in pairs:
                val = smart_truncate(data.get(key, "Loading..."))
                html += f"<div class='semi-card'><div class='card-key'>{lbl}</div><div class='card-val'>{val}</div></div>"
            return html

        result = {}
        nodes_done = 0
        total_nodes = 5
        st.session_state.thread_id = f"session_{int(time.time())}_{final_ticker}"

        try:
            for chunk in app.stream(
                {"ticker": final_ticker},
                config={"configurable": {"thread_id": st.session_state.thread_id}},
                stream_mode="updates"
            ):
                for node_name, node_data in chunk.items():
                    print(f"[DEBUG] node_name={node_name}, node_data={node_data}", flush=True)
                    for k, v in node_data.items():
                        if v:
                            result[k] = v
                    nodes_done += 1
                    pct = int((nodes_done / total_nodes) * 100)

                    if node_name == "fetch_macro":
                        progress_bar.progress(pct, text="Macroeconomic factors loaded")
                        ph_macro.markdown(make_cards(result, [
                            ("CPI","cpi"),("PPI","ppi"),("Fed Rate","fed_rate"),("USD Index","usd_index")
                        ], "Macroeconomic"), unsafe_allow_html=True)

                    elif node_name == "fetch_fundamental":
                        progress_bar.progress(pct, text="Fundamental factors loaded")
                        ph_fund.markdown(make_cards(result, [
                            ("P/E Ratio","pe_ratio"),("Market Cap","market_cap"),
                            ("Earnings Guidance","earnings_guidance"),("Insider Selling","insider_selling")
                        ], "Fundamental"), unsafe_allow_html=True)

                    elif node_name == "fetch_market":
                        progress_bar.progress(pct, text="Market intelligence loaded")
                        ph_market.markdown(make_cards(result, [
                            ("Sector Rally","sector_rally"),("Technical Signal","technical_signal"),
                            ("Analyst Ratings","analyst_ratings"),("Sell-the-News","sell_the_news")
                        ], "Market Intelligence"), unsafe_allow_html=True)

                    elif node_name == "fetch_external":
                        progress_bar.progress(pct, text="External signals loaded")
                        ph_external.markdown(make_cards(result, [
                            ("Geopolitics","geopolitics"),("Supply Chain","supply_chain"),
                            ("News Sentiment","news_sentiment"),("Capital Rotation","capital_rotation"),
                            ("Competitor Contagion","competitor_contagion"),("Beta","beta")
                        ], "External Signals"), unsafe_allow_html=True)

                    elif node_name == "generate_prediction":
                        progress_bar.progress(100, text="Prediction complete")

            progress_bar.empty()

            st.session_state.result = result
            st.session_state.ticker = final_ticker
            st.session_state.followup_history = []

            pred_text = result.get("prediction", "")
            up_prob_hist = "50%"
            for line in pred_text.split("\n"):
                if "UP_PROBABILITY:" in line:
                    up_prob_hist = line.split(":")[-1].strip()[:5]
                    break

            save_history(final_ticker, up_prob_hist, uk_time_str(), result, st.session_state.followup_history)
            st.session_state.history = load_history()
            if st.session_state.history:
                st.session_state.current_history_id = st.session_state.history[0]["id"]

            if st.session_state.last_ticker != final_ticker:
                st.session_state.last_ticker = final_ticker

            st.rerun()

        except GeneratorExit:
            pass
        except Exception as e:
            # Nicer error UX: toast + persistent card with retry hint
            try:
                st.toast(f"Analysis failed — {type(e).__name__}", icon="⚠️")
            except Exception:
                pass
            st.error(
                f"**Analysis failed.**  \n"
                f"`{type(e).__name__}: {str(e)[:200]}`  \n\n"
                "This usually clears up on retry. If it persists, Yahoo Finance may be rate-limited — "
                "wait ~30 seconds and try again."
            )

elif analyse and not ticker_input:
    st.markdown("<div class='val-error'>Warning: Please enter a ticker symbol or company name first.</div>", unsafe_allow_html=True)

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

    scores = result.get("scores", {})

    if scores:
        st.markdown("<div class='sec-label'>Interactive causal map</div>", unsafe_allow_html=True)
        try:
            render_causal_map(ticker, scores, {k: smart_truncate(result.get(k, ""), 700) for k in FACTOR_KEYS})
        except Exception as e:
            st.caption(f"Causal map unavailable: {e}")

    st.markdown("<div class='sec-label'>Macroeconomic</div>", unsafe_allow_html=True)
    for label, key in [("CPI","cpi"),("PPI","ppi"),("Fed Rate","fed_rate"),("USD Index","usd_index")]:
        st.markdown(f"<div class='semi-card'><div class='card-key'>{label}</div><div class='card-val'>{smart_truncate(result.get(key,'N/A'))}</div>{score_badge(key, scores)}</div>", unsafe_allow_html=True)

    st.markdown("<div class='sec-label'>Fundamental</div>", unsafe_allow_html=True)
    for label, key in [("P/E Ratio","pe_ratio"),("Market Cap","market_cap"),("Earnings Guidance","earnings_guidance"),("Insider Selling","insider_selling")]:
        st.markdown(f"<div class='semi-card'><div class='card-key'>{label}</div><div class='card-val'>{smart_truncate(result.get(key,'N/A'))}</div>{score_badge(key, scores)}</div>", unsafe_allow_html=True)

    st.markdown("<div class='sec-label'>Market Intelligence</div>", unsafe_allow_html=True)
    for label, key in [("Sector Rally","sector_rally"),("Technical Signal","technical_signal"),("Analyst Ratings","analyst_ratings"),("Sell-the-News","sell_the_news")]:
        st.markdown(f"<div class='semi-card'><div class='card-key'>{label}</div><div class='card-val'>{smart_truncate(result.get(key,'N/A'))}</div>{score_badge(key, scores)}</div>", unsafe_allow_html=True)

    st.markdown("<div class='sec-label'>External Signals</div>", unsafe_allow_html=True)
    for label, key in [("Geopolitics","geopolitics"),("Supply Chain","supply_chain"),("News Sentiment","news_sentiment"),("Capital Rotation","capital_rotation"),("Competitor Contagion","competitor_contagion"),("Beta","beta")]:
        if key == "competitor_contagion":
            val = str(result.get(key, "N/A"))
        else:
            val = smart_truncate(result.get(key, "N/A"))
        st.markdown(f"<div class='semi-card'><div class='card-key'>{label}</div><div class='card-val'>{val}</div>{score_badge(key, scores)}</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color:#3A4658;margin:24px 0'>", unsafe_allow_html=True)
    st.markdown("<div style='font-family:Inter,sans-serif;font-size:1rem;font-weight:600;color:#EDF0F5;margin-bottom:14px'>Prediction</div>", unsafe_allow_html=True)

    p1, p2, p3 = st.columns([1.2, 1.2, 2.6])
    with p1:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-lbl'>Upside</div>
            <div class='metric-num-up'>{up_prob}%</div>
            <div class='bar-track'><div class='bar-up' style='width:{up_prob}%'></div></div>
        </div>""", unsafe_allow_html=True)
    with p2:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-lbl'>Downside</div>
            <div class='metric-num-dn'>{down_prob}%</div>
            <div class='bar-track'><div class='bar-dn' style='width:{down_prob}%'></div></div>
        </div>""", unsafe_allow_html=True)
    with p3:
        bullish_html = "".join([f"<div style='font-size:0.8rem;color:#34D399;margin-bottom:4px'>+ {b}</div>" for b in bullish[:3]])
        bearish_html = "".join([f"<div style='font-size:0.8rem;color:#F87171;margin-bottom:4px'>- {b}</div>" for b in bearish[:3]])
        st.markdown(f"""
        <div class='metric-card' style='text-align:left'>
            <div style='display:grid;grid-template-columns:1fr 1fr;gap:16px'>
                <div><div style='font-size:0.62rem;color:#9AA6B8;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px'>Bullish</div>{bullish_html}</div>
                <div><div style='font-size:0.62rem;color:#9AA6B8;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px'>Bearish</div>{bearish_html}</div>
            </div>
            <div style='margin-top:12px;font-size:0.7rem;color:#9AA6B8'>Confidence: <strong style='color:#8BB8FF'>{confidence}</strong></div>
        </div>""", unsafe_allow_html=True)

    if reasoning:
        st.markdown(f"<div class='reasoning-card'>{reasoning}</div>", unsafe_allow_html=True)

    # Keep URL in sync with current ticker so the page is shareable
    set_ticker_in_query(ticker)

    # Share + export actions
    st.markdown("<div style='font-family:Inter,sans-serif;font-size:0.75rem;color:#A4AFC0;margin:16px 0 4px;text-transform:uppercase;letter-spacing:0.08em'>Share &amp; Export</div>", unsafe_allow_html=True)
    _share_col1, _share_col2 = st.columns([2, 1])
    with _share_col1:
        render_copy_link_button(ticker)
    with _share_col2:
        render_download_pdf_button(
            ticker=ticker,
            prediction=f"UP {up_prob}%" if up_prob >= down_prob else f"DOWN {down_prob}%",
            up_pct=up_prob,
            down_pct=down_prob,
            scores=scores,
            reasoning=reasoning,
            timestamp=uk_time_str(),
        )

    st.markdown("<hr style='border-color:#3A4658;margin:24px 0'>", unsafe_allow_html=True)
    st.markdown("<div style='font-family:Inter,sans-serif;font-size:0.95rem;font-weight:600;color:#EDF0F5;margin-bottom:6px'>Ask a follow-up question</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.75rem;color:#A4AFC0;margin-bottom:12px'>Ask about factors, what-if scenarios, or deeper insights</div>", unsafe_allow_html=True)

    for msg in st.session_state.followup_history:
        if msg["role"] == "user":
            st.markdown(f"<div class='user-bubble'>{msg['content']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='bot-bubble'><div style='font-size:0.65rem;color:#8BB8FF;font-weight:600;margin-bottom:4px'>SEMIBOT</div>{msg['content']}</div>", unsafe_allow_html=True)

    fq1, fq2 = st.columns([5, 1])
    with fq1:
        if "followup_input_counter" not in st.session_state:
            st.session_state.followup_input_counter = 0
        followup_q = st.text_input(
            "", placeholder="e.g. How does P/E ratio affect MU? What if Fed rate drops?",
            label_visibility="collapsed", key=f"followup_input_{st.session_state.followup_input_counter}"
        )
    with fq2:
        ask_button = st.button("Ask ->", use_container_width=True, key="ask_btn", type="primary")

    if ask_button and followup_q:
        historical_context = get_historical_context(ticker)
        analysis_context = f"""You are analyzing {ticker} stock. Here is the complete 18-factor analysis:

LONG_TERM_MEMORY: {historical_context}
The above line lists ONLY past UP% values for {ticker} with timestamps, most recent first - nothing else. It does NOT include individual factor scores (P/E, CPI, Fed Rate, etc.) from past sessions. When asked to compare the current UP%/DOWN% result to past sessions, cite the specific past UP% value directly (e.g. "your last {ticker} analysis showed UP 45%, and this one is higher at 48%"). If asked about a specific FACTOR SCORE from a past session (not the overall UP%), you MUST say you don't have that level of historical detail - only overall UP% and timestamp are stored in long-term memory, not individual factor values. Never substitute the CURRENT analysis's factor value and present it as if it were from a past session.

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
- If asked "who are you": say "I am SemiBot - an AI-powered semiconductor equity analyser built on 18 causal factors. Created by Raj Tejpal Khatik at the University of Warwick."
- If asked "who created you" or "who is Raj" or "who made you": say "I was created by Raj Tejpal Khatik, an MSc Applied AI student at the University of Warwick."
- Never say you are ChatGPT, Claude, or any other AI.

TOPIC RULES: Answer questions about companies, stocks, markets, finance, economics, business, or technology freely and helpfully, including CEOs, executives, share prices, company history, products, competitors, or comparisons for {ticker} or ANY other company.
A "what is the current price of X" question is ALWAYS on-topic and answerable - use the LIVE PRICES data below if the ticker is listed there. This is NOT a refusal-worthy request under any circumstance.
Only refuse if the question has absolutely nothing to do with business, finance, companies, or technology, such as asking for a recipe, a poem, medical advice, or help with unrelated homework. If there is any plausible connection to business/finance/tech, just answer it.
Refusal message (use only for clearly unrelated requests): "I'm focused on semiconductor equity analysis and can't help with that. Feel free to ask me about {ticker}, market factors, or the analysis above!"
{_live_price_block()}"""

        st.session_state.followup_history.append({"role": "user", "content": followup_q})

        from graph.nodes import llm
        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

        messages = [SystemMessage(content=analysis_context)]
        for prev_msg in st.session_state.followup_history[-6:-1]:
            if prev_msg["role"] == "user":
                messages.append(HumanMessage(content=prev_msg["content"]))
            else:
                messages.append(AIMessage(content=prev_msg["content"]))
        messages.append(HumanMessage(content=followup_q))

        with st.chat_message("assistant"):
            try:
                response_text = st.write_stream(
                    chunk.content for chunk in llm.stream(messages)
                    if hasattr(chunk, "content") and chunk.content
                )
            except GeneratorExit:
                response_text = ""

        st.session_state.followup_history.append({"role": "assistant", "content": response_text})
        log_event("chat", question=followup_q, reply=response_text)
        if st.session_state.current_history_id:
            update_followup(st.session_state.current_history_id, st.session_state.followup_history)
        st.session_state.followup_input_counter += 1
        st.rerun()

    elif ask_button and not followup_q:
        st.markdown("<div class='val-error'>Warning: Please type a question first.</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color:#3A4658;margin:24px 0'>", unsafe_allow_html=True)
    st.markdown("<div style='font-family:Inter,sans-serif;font-size:0.95rem;font-weight:600;color:#EDF0F5;margin-bottom:12px'>Email Summary</div>", unsafe_allow_html=True)

    em1, em2 = st.columns([4, 1])
    with em1:
        user_email = st.text_input("", placeholder="Enter your email to receive analysis summary...", label_visibility="collapsed", key="email_input")
    with em2:
        send_button = st.button("Send", use_container_width=True, type="primary")

    if send_button and user_email:
        try:
            bullish_text = "\n".join([f"  + {b}" for b in bullish[:3]])
            bearish_text = "\n".join([f"  - {b}" for b in bearish[:3]])
            email_body = f"""SEMICONDUCTOR EQUITY ANALYSIS REPORT
=====================================
Ticker: {ticker} | Date: {time.strftime("%d %B %Y, %H:%M")}
Generated by: SemiBot - 18-Factor Agentic RAG System
University of Warwick MSc Applied AI Research

PREDICTION
UP Probability: {up_prob}% | DOWN Probability: {down_prob}% | Confidence: {confidence}

BULLISH FACTORS
{bullish_text}

BEARISH FACTORS
{bearish_text}

REASONING: {reasoning}

MACROECONOMIC
CPI: {result.get('cpi','N/A')} | PPI: {result.get('ppi','N/A')} | Fed Rate: {result.get('fed_rate','N/A')} | USD: {result.get('usd_index','N/A')}

FUNDAMENTAL
P/E: {result.get('pe_ratio','N/A')} | Market Cap: {result.get('market_cap','N/A')} | EPS: {result.get('earnings_guidance','N/A')} | Insider: {result.get('insider_selling','N/A')}

MARKET INTELLIGENCE
SOXX: {result.get('sector_rally','N/A')} | Technical: {result.get('technical_signal','N/A')} | Analyst: {result.get('analyst_ratings','N/A')}

EXTERNAL SIGNALS
Geo: {str(result.get('geopolitics','N/A'))[:80]} | News: {str(result.get('news_sentiment','N/A'))[:80]} | Beta: {result.get('beta','N/A')}

DISCLAIMER: AI research tool only. Not financial advice.
SemiBot v1.0 | University of Warwick | MSc Applied AI | ACM FinNLP
"""
            sender_email = os.getenv("SENDER_EMAIL")
            sender_password = os.getenv("SENDER_APP_PASSWORD")
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = user_email
            msg['Subject'] = f"SemiBot Analysis - {ticker} - {time.strftime('%d %b %Y')}"
            msg.attach(MIMEText(email_body, 'plain'))
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, user_email, msg.as_string())
            server.quit()
            st.success(f"Report sent to {user_email}")
        except Exception as e:
            st.error(f"Email failed: {str(e)}")

    elif send_button and not user_email:
        st.markdown("<div class='val-error'>Warning: Please enter your email address.</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class='disclaimer'>
        Warning: This analysis is generated by an AI research tool for informational and academic purposes only.
        It does NOT constitute financial advice. Always consult a qualified financial advisor.
    </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

render_ticker_tape()

# Clear the full-screen loader now that the page has fully rendered.
_loading_placeholder.empty()