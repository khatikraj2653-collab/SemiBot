"""
Floating 'Ask SemiBot' chat bubble — same underlying LLM/grounding logic
used by the existing inline follow-up Q&A, just presented as a persistent
floating widget (like the portfolio site's chat bubble) instead of an
inline box. Usable from both the landing page and the analysis page.
"""
import streamlit as st
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from log_client import log_event

GENERIC_SYSTEM_PROMPT = """You are SemiBot, an 18-factor agentic RAG system for semiconductor equity \
analysis, created by Raj Tejpal Khatik, an MSc Applied AI student at the University of Warwick, \
targeting ACM FinNLP.

- If asked "who are you": say "I am SemiBot - an AI-powered semiconductor equity analyser built on \
18 causal factors. Created by Raj Tejpal Khatik at the University of Warwick."
- If asked "who created you" or "who is Raj" or "who made you": say "I was created by Raj Tejpal \
Khatik, an MSc Applied AI student at the University of Warwick."
- Never say you are ChatGPT, Claude, or any other AI.
- No analysis has been run yet in this session, so you don't have specific factor data for any \
ticker right now. If asked about a specific stock's current prediction, tell the user to run an \
analysis first (there's an "Analyse" button on the page) and offer to answer general questions about \
semiconductor companies, the sector, or how SemiBot works in the meantime.

TOPIC RULES: Answer questions about companies, stocks, markets, finance, economics, business, or \
technology freely and helpfully, including CEOs, executives, share prices, company history, \
products, competitors, or comparisons for any semiconductor company or the sector broadly.
Only refuse if the question has absolutely nothing to do with business, finance, companies, or \
technology, such as asking for a recipe, a poem, medical advice, or unrelated homework help.
Refusal message (use only for clearly unrelated requests): "I'm focused on semiconductor equity \
analysis and can't help with that. Feel free to ask me about semiconductor stocks, market factors, \
or how SemiBot works!"
"""

BUBBLE_CSS = """
<style>
.st-key-semibot_bubble_toggle {
    position: fixed !important;
    bottom: 24px !important;
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
    bottom: 94px !important;
    right: 24px !important;
    width: 372px !important;
    max-width: calc(100vw - 32px) !important;
    max-height: 520px !important;
    overflow-y: auto !important;
    background: #060B14 !important;
    border: 1px solid rgba(0,140,255,0.25) !important;
    border-radius: 16px !important;
    padding: 18px 16px 14px !important;
    z-index: 999998 !important;
    box-shadow: 0 16px 48px rgba(0,0,0,0.55) !important;
}
.semibot-bubble-title {
    font-family: 'Space Grotesk', sans-serif; font-size: 0.95rem; font-weight: 700;
    color: #D0E8FF; margin-bottom: 2px;
}
.semibot-bubble-sub {
    font-size: 0.68rem; color: #5A8AAF; margin-bottom: 12px;
}
.semibot-bubble-user {
    background: linear-gradient(135deg,rgba(0,70,180,0.3),rgba(0,130,255,0.2));
    border: 1px solid rgba(0,140,255,0.25);
    border-radius: 14px 14px 4px 14px;
    padding: 9px 12px; margin: 5px 0 5px auto;
    font-size: 0.8rem; color: #E8F4FF; line-height: 1.55;
    max-width: 84%; display: table; margin-left: auto;
}
.semibot-bubble-bot {
    background: rgba(0,20,55,0.75);
    border: 1px solid rgba(0,80,160,0.2);
    border-radius: 14px 14px 14px 4px;
    padding: 10px 12px; margin: 5px 0;
    font-size: 0.8rem; color: #F0F8FF; line-height: 1.55;
    max-width: 88%;
}
.st-key-semibot_bubble_panel .stTextInput input {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(0,140,255,0.2) !important;
    color: #E8F4FF !important;
    font-size: 0.82rem !important;
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

    st.markdown(BUBBLE_CSS, unsafe_allow_html=True)

    with st.container(key="semibot_bubble_toggle"):
        icon = "×" if st.session_state.bubble_open else "💬"
        if st.button(icon, key="semibot_bubble_toggle_btn"):
            st.session_state.bubble_open = not st.session_state.bubble_open
            st.rerun()

    if not st.session_state.bubble_open:
        return

    with st.container(key="semibot_bubble_panel"):
        st.markdown(
            "<div class='semibot-bubble-title'>Ask SemiBot</div>"
            "<div class='semibot-bubble-sub'>Semiconductor market Q&amp;A - won't answer off-topic questions</div>",
            unsafe_allow_html=True,
        )

        for msg in st.session_state.bubble_history:
            css_class = "semibot-bubble-user" if msg["role"] == "user" else "semibot-bubble-bot"
            st.markdown(f"<div class='{css_class}'>{msg['content']}</div>", unsafe_allow_html=True)

        q_col, btn_col = st.columns([5, 1])
        with q_col:
            question = st.text_input(
                "", placeholder="Ask about semiconductor stocks...",
                label_visibility="collapsed",
                key=f"bubble_input_{st.session_state.bubble_input_counter}",
            )
        with btn_col:
            ask = st.button("Ask", use_container_width=True, key="semibot_bubble_ask_btn")

        if ask and question:
            system_prompt = None
            if get_system_prompt:
                try:
                    system_prompt = get_system_prompt()
                except Exception:
                    system_prompt = None
            if not system_prompt:
                system_prompt = GENERIC_SYSTEM_PROMPT

            st.session_state.bubble_history.append({"role": "user", "content": question})

            from graph.nodes import llm

            messages = [SystemMessage(content=system_prompt)]
            for prev in st.session_state.bubble_history[-6:-1]:
                if prev["role"] == "user":
                    messages.append(HumanMessage(content=prev["content"]))
                else:
                    messages.append(AIMessage(content=prev["content"]))
            messages.append(HumanMessage(content=question))

            try:
                reply = llm.invoke(messages).content
            except Exception:
                reply = "Sorry, I couldn't process that right now. Please try again shortly."

            st.session_state.bubble_history.append({"role": "assistant", "content": reply})
            log_event("chat", question=question, reply=reply)
            st.session_state.bubble_input_counter += 1
            st.rerun()
