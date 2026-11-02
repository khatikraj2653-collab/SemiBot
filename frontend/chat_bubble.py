"""
Floating 'Ask SemiBot' chat bubble — same underlying LLM/grounding logic
used by the existing inline follow-up Q&A, just presented as a persistent
floating widget (like the portfolio site's chat bubble) instead of an
inline box. Usable from both the landing page and the analysis page.
"""
import os
import streamlit as st
import yfinance as yf
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from log_client import log_event

def _get_llm():
    return ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"), temperature=0)

LIVE_PRICE_TICKERS = ["MU", "NVDA", "AMD", "INTC", "TSM", "ASML", "QCOM", "AVGO", "AMAT", "LRCX", "ARM", "TXN", "ADI", "MCHP", "ON"]


@st.cache_data(ttl=900)
def get_live_prices_text():
    """Plain-text snapshot of current prices for commonly-asked tickers,
    so the bubble can answer 'what's the price of X' without requiring a
    full analysis run first. Cached 15 min to limit yfinance calls."""
    try:
        data = yf.download(
            tickers=" ".join(LIVE_PRICE_TICKERS), period="5d", interval="1d",
            group_by="ticker", threads=True, progress=False,
        )
        lines = []
        for t in LIVE_PRICE_TICKERS:
            try:
                closes = data[t]["Close"].dropna()
                if len(closes) < 2:
                    continue
                price = round(float(closes.iloc[-1]), 2)
                prev = round(float(closes.iloc[-2]), 2)
                pct = round((price - prev) / prev * 100, 2)
                sign = "+" if pct >= 0 else ""
                lines.append(f"{t}: ${price} ({sign}{pct}%)")
            except Exception:
                continue
        return "; ".join(lines) if lines else None
    except Exception:
        return None


def _live_price_block():
    prices = get_live_prices_text()
    if not prices:
        return ""
    return f"\n\nLIVE PRICES (last close, refreshed periodically): {prices}\nYou CAN and SHOULD use these to answer 'what's the current price of X' for any ticker listed above."


GENERIC_SYSTEM_PROMPT_TEMPLATE = """You are SemiBot, an 18-factor agentic RAG system for semiconductor equity \
analysis, created by Raj Tejpal Khatik, an MSc Applied AI student at the University of Warwick, \
targeting ACM FinNLP.

- If asked "who are you": say "I am SemiBot - an AI-powered semiconductor equity analyser built on \
18 causal factors. Created by Raj Tejpal Khatik at the University of Warwick."
- If asked "who created you" or "who is Raj" or "who made you": say "I was created by Raj Tejpal \
Khatik, an MSc Applied AI student at the University of Warwick."
- Never say you are ChatGPT, Claude, or any other AI.
- No full 18-factor analysis has been run yet in this session, so you don't have factor-level data \
(P/E, macro scores, sentiment, etc.) for any ticker right now. If asked for a full prediction/analysis, \
tell the user to run one first (there's an "Analyse" button on the page). For a simple current price, \
use the LIVE PRICES data below if the ticker is listed there.

TOPIC RULES: Answer questions about companies, stocks, markets, finance, economics, business, or \
technology freely and helpfully, including CEOs, executives, share prices, company history, \
products, competitors, or comparisons for any semiconductor company or the sector broadly.
Only refuse if the question has absolutely nothing to do with business, finance, companies, or \
technology, such as asking for a recipe, a poem, medical advice, or unrelated homework help.
Refusal message (use only for clearly unrelated requests): "I'm focused on semiconductor equity \
analysis and can't help with that. Feel free to ask me about semiconductor stocks, market factors, \
or how SemiBot works!"{live_prices}
"""


def build_generic_prompt():
    return GENERIC_SYSTEM_PROMPT_TEMPLATE.format(live_prices=_live_price_block())

BUBBLE_CSS = """
<style>
.st-key-semibot_bubble_toggle {
    position: fixed !important;
    bottom: 84px !important;
    right: 24px !important;
    z-index: 999999 !important;
    width: 58px !important;
}
.st-key-semibot_bubble_toggle button {
    width: 58px !important;
    height: 58px !important;
    border-radius: 50% !important;
    background: linear-gradient(135deg, #0055FF, #00AAFF) !important;
    color: #fff !important;
    font-size: 26px !important;
    line-height: 1 !important;
    box-shadow: 0 4px 22px rgba(0,140,255,0.55) !important;
    border: none !important;
    padding: 0 !important;
}
.st-key-semibot_bubble_toggle button:hover {
    box-shadow: 0 6px 30px rgba(0,180,255,0.7) !important;
    transform: translateY(-2px);
}
.st-key-semibot_bubble_panel {
    position: fixed !important;
    bottom: 154px !important;
    right: 24px !important;
    width: 380px !important;
    max-width: calc(100vw - 32px) !important;
    max-height: calc(100vh - 140px) !important;
    background: #060B14 !important;
    border: 1px solid rgba(0,140,255,0.25) !important;
    border-radius: 16px !important;
    padding: 0 !important;
    z-index: 999998 !important;
    box-shadow: 0 16px 48px rgba(0,0,0,0.55) !important;
    display: flex !important;
    flex-direction: column !important;
    overflow: hidden !important;
}
.st-key-semibot_bubble_header {
    padding: 14px 18px 10px !important;
    border-bottom: 1px solid rgba(0,140,255,0.15) !important;
    flex-shrink: 0 !important;
}
.semibot-bubble-title {
    font-family: 'Space Grotesk', sans-serif; font-size: 0.95rem; font-weight: 700;
    color: #D0E8FF; margin-bottom: 2px;
}
.semibot-bubble-sub {
    font-size: 0.68rem; color: #5A8AAF;
}
.st-key-semibot_bubble_messages {
    flex: 1 1 auto !important;
    overflow-y: auto !important;
    padding: 12px 16px !important;
    min-height: 120px !important;
    max-height: 360px !important;
}
.semibot-bubble-messages-inner {
    display: flex;
    flex-direction: column;
    gap: 8px;
}
.semibot-bubble-user {
    background: linear-gradient(135deg,rgba(0,70,180,0.3),rgba(0,130,255,0.2));
    border: 1px solid rgba(0,140,255,0.25);
    border-radius: 14px 14px 4px 14px;
    padding: 9px 12px;
    font-size: 0.8rem; color: #E8F4FF; line-height: 1.55;
    max-width: 84%; align-self: flex-end;
}
.semibot-bubble-bot {
    background: rgba(0,20,55,0.75);
    border: 1px solid rgba(0,80,160,0.2);
    border-radius: 14px 14px 14px 4px;
    padding: 10px 12px;
    font-size: 0.8rem; color: #F0F8FF; line-height: 1.55;
    max-width: 88%; align-self: flex-start;
}
.semibot-bubble-typing {
    font-size: 0.75rem; color: #5A8AAF; align-self: flex-start;
    padding: 2px 4px;
}
.st-key-semibot_bubble_inputrow {
    padding: 10px 14px 14px !important;
    border-top: 1px solid rgba(0,140,255,0.15) !important;
    flex-shrink: 0 !important;
}
.st-key-semibot_bubble_panel [data-baseweb="base-input"],
.st-key-semibot_bubble_panel [data-baseweb="input"] {
    background: #0C1526 !important;
    border: 1px solid rgba(0,140,255,0.3) !important;
    border-radius: 8px !important;
}
.st-key-semibot_bubble_panel .stTextInput input {
    background: #0C1526 !important;
    color: #E8F4FF !important;
    font-size: 0.82rem !important;
    -webkit-text-fill-color: #E8F4FF !important;
}
.st-key-semibot_bubble_panel .stTextInput input::placeholder {
    color: #5A8AAF !important;
    opacity: 1 !important;
}
</style>
"""


def render_chat_bubble(get_system_prompt=None):
    """
    get_system_prompt: optional callable() -> str, builds richer context
    (e.g. current ticker analysis) based on session state at ask-time.
    Falls back to the generic SemiBot identity prompt if not provided or
    if no analysis context is currently available.
    """
    if "bubble_open" not in st.session_state:
        st.session_state.bubble_open = False
    if "bubble_history" not in st.session_state:
        st.session_state.bubble_history = []
    if "bubble_input_counter" not in st.session_state:
        st.session_state.bubble_input_counter = 0
    if "bubble_thinking" not in st.session_state:
        st.session_state.bubble_thinking = False

    st.markdown(BUBBLE_CSS, unsafe_allow_html=True)

    with st.container(key="semibot_bubble_toggle"):
        icon = "×" if st.session_state.bubble_open else "💬"
        st.button(icon, key="semibot_bubble_toggle_btn",
                                    on_click=lambda: st.session_state.update({"bubble_open": not st.session_state.bubble_open}))

    if not st.session_state.bubble_open:
        return

    with st.container(key="semibot_bubble_panel"):
        with st.container(key="semibot_bubble_header"):
            st.markdown(
                "<div class='semibot-bubble-title'>Ask SemiBot</div>"
                "<div class='semibot-bubble-sub'>Semiconductor market Q&amp;A - won't answer off-topic questions</div>",
                unsafe_allow_html=True,
            )

        with st.container(key="semibot_bubble_messages"):
            parts = ["<div class='semibot-bubble-messages-inner'>"]
            for msg in st.session_state.bubble_history:
                css_class = "semibot-bubble-user" if msg["role"] == "user" else "semibot-bubble-bot"
                parts.append(f"<div class='{css_class}'>{msg['content']}</div>")
            if st.session_state.bubble_thinking:
                parts.append("<div class='semibot-bubble-typing'>Thinking...</div>")
            parts.append("</div>")
            st.markdown("".join(parts), unsafe_allow_html=True)

        with st.container(key="semibot_bubble_inputrow"):
            q_col, btn_col = st.columns([5, 1])
            with q_col:
                question = st.text_input(
                    "", placeholder="Ask about semiconductor stocks...",
                    label_visibility="collapsed",
                    key=f"bubble_input_{st.session_state.bubble_input_counter}",
                    disabled=st.session_state.bubble_thinking,
                )
            with btn_col:
                ask = st.button(
                    "Ask", use_container_width=True, key="semibot_bubble_ask_btn",
                    disabled=st.session_state.bubble_thinking,
                )

            if ask and question and not st.session_state.bubble_thinking:
                st.session_state.bubble_history.append({"role": "user", "content": question})
                st.session_state.bubble_thinking = True
                st.session_state.bubble_input_counter += 1
                st.rerun()

    if st.session_state.bubble_thinking:
        last_question = st.session_state.bubble_history[-1]["content"]
        system_prompt = None
        if get_system_prompt:
            try:
                system_prompt = get_system_prompt()
            except Exception:
                system_prompt = None
        if not system_prompt:
            system_prompt = build_generic_prompt()

        try:
            llm = _get_llm()
            messages = [SystemMessage(content=system_prompt)]
            for prev in st.session_state.bubble_history[-7:-1]:
                if prev["role"] == "user":
                    messages.append(HumanMessage(content=prev["content"]))
                else:
                    messages.append(AIMessage(content=prev["content"]))
            messages.append(HumanMessage(content=last_question))
            reply = llm.invoke(messages).content
        except Exception:
            reply = "Sorry, I couldn't process that right now. Please try again shortly."

        st.session_state.bubble_history.append({"role": "assistant", "content": reply})
        log_event("chat", question=last_question, reply=reply)
        st.session_state.bubble_thinking = False
        st.rerun()
