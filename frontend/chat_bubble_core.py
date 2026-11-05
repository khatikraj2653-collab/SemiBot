"""
Shared floating chat bubble for SemiBot/GoldBot/SilverBot.

Each bot calls `render_bubble(BubbleConfig(...))` with its own theme colors,
title, placeholder, system prompt, and optional pre-message context hook.

Duplicated as-is in each bot's frontend/ so each repo remains an independent
Streamlit Cloud deployment — do not import across repos.
"""
import os
from dataclasses import dataclass, field
from typing import Callable, Optional

import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

try:
    from log_client import log_event
except Exception:
    def log_event(*a, **kw):
        pass


@dataclass
class BubbleTheme:
    slug: str
    accent: str
    accent_hover: str
    text_primary: str
    text_secondary: str
    bg_panel: str
    bg_input: str
    bubble_icon_color: str
    hair: str = ""


@dataclass
class BubbleConfig:
    theme: BubbleTheme
    title: str
    subtitle: str
    placeholder: str
    system_prompt: str
    pre_message: Optional[Callable[[], str]] = None
    system_prompt_fn: Optional[Callable[[], Optional[str]]] = None
    model: str = "gpt-4o-mini"


def _build_css(t: BubbleTheme) -> str:
    s = t.slug
    accent = t.accent
    accent_hover = t.accent_hover
    t1 = t.text_primary
    t2 = t.text_secondary
    bg = t.bg_panel
    bgi = t.bg_input
    ic = t.bubble_icon_color
    hair = t.hair or "rgba(245,235,208,.14)"
    return f"""
<style>
.st-key-{s}_bubble_toggle {{
    position: fixed !important;
    bottom: 84px !important;
    right: 24px !important;
    z-index: 999999 !important;
    width: 58px !important;
}}
.st-key-{s}_bubble_toggle button {{
    width: 58px !important;
    height: 58px !important;
    border-radius: 50% !important;
    background: {accent} !important;
    color: {ic} !important;
    font-size: 26px !important;
    line-height: 1 !important;
    border: none !important;
    padding: 0 !important;
    box-shadow: none !important;
}}
.st-key-{s}_bubble_toggle button:hover {{
    background: {accent_hover} !important;
    box-shadow: none !important;
    transform: none;
}}
.st-key-{s}_bubble_panel {{
    position: fixed !important;
    bottom: 154px !important;
    right: 24px !important;
    width: 380px !important;
    max-width: calc(100vw - 32px) !important;
    max-height: calc(100vh - 140px) !important;
    background: {bg} !important;
    border: 1px solid {hair} !important;
    border-radius: 20px !important;
    padding: 0 !important;
    z-index: 999998 !important;
    display: flex !important;
    flex-direction: column !important;
    overflow: hidden !important;
    box-shadow: none !important;
}}
.st-key-{s}_bubble_header {{
    padding: 14px 18px 10px !important;
    border-bottom: 1px solid {hair} !important;
    flex-shrink: 0 !important;
}}
.{s}-bubble-title {{
    font-family: 'Space Grotesk', sans-serif; font-size: 0.95rem; font-weight: 700;
    color: {t1}; margin-bottom: 2px;
}}
.{s}-bubble-sub {{
    font-size: 0.68rem; color: {t2};
}}
.st-key-{s}_bubble_messages {{
    flex: 1 1 auto !important;
    overflow-y: auto !important;
    padding: 12px 16px !important;
    min-height: 120px !important;
    max-height: 360px !important;
}}
.{s}-bubble-messages-inner {{
    display: flex; flex-direction: column; gap: 8px;
}}
.{s}-bubble-user {{
    background: {accent}; border: 0; color: {ic};
    border-radius: 16px 16px 4px 16px;
    padding: 9px 12px;
    font-size: 0.8rem; line-height: 1.55;
    max-width: 84%; align-self: flex-end;
}}
.{s}-bubble-bot {{
    background: {bgi}; border: 1px solid {hair};
    border-radius: 16px 16px 16px 4px;
    padding: 10px 12px;
    font-size: 0.8rem; color: {t1}; line-height: 1.55;
    max-width: 88%; align-self: flex-start;
}}
.{s}-bubble-typing {{
    font-size: 0.75rem; color: {t2}; align-self: flex-start;
    padding: 2px 4px;
}}
.st-key-{s}_bubble_inputrow {{
    padding: 10px 14px 14px !important;
    border-top: 1px solid {hair} !important;
    flex-shrink: 0 !important;
}}
.st-key-{s}_bubble_panel [data-baseweb="base-input"],
.st-key-{s}_bubble_panel [data-baseweb="input"] {{
    background: {bgi} !important;
    border: 1px solid {hair} !important;
    border-radius: 12px !important;
}}
.st-key-{s}_bubble_panel .stTextInput input {{
    background: transparent !important;
    color: {t1} !important;
    font-size: 0.82rem !important;
    -webkit-text-fill-color: {t1} !important;
}}
.st-key-{s}_bubble_panel .stTextInput input::placeholder {{
    color: {t2} !important;
    opacity: 1 !important;
}}
</style>
"""


def _get_llm(model: str):
    return ChatOpenAI(model=model, api_key=os.getenv("OPENAI_API_KEY"), temperature=0)


def render_bubble(cfg: BubbleConfig):
    """Floating chat bubble widget. Call once per page."""
    slug = cfg.theme.slug
    if "bubble_open" not in st.session_state:
        st.session_state.bubble_open = False
    if "bubble_history" not in st.session_state:
        st.session_state.bubble_history = []
    if "bubble_input_counter" not in st.session_state:
        st.session_state.bubble_input_counter = 0
    if "bubble_thinking" not in st.session_state:
        st.session_state.bubble_thinking = False

    st.markdown(_build_css(cfg.theme), unsafe_allow_html=True)

    with st.container(key=f"{slug}_bubble_toggle"):
        icon = "×" if st.session_state.bubble_open else "💬"
        st.button(
            icon, key=f"{slug}_bubble_toggle_btn",
            on_click=lambda: st.session_state.update({"bubble_open": not st.session_state.bubble_open}),
        )

    if not st.session_state.bubble_open:
        return

    with st.container(key=f"{slug}_bubble_panel"):
        with st.container(key=f"{slug}_bubble_header"):
            st.markdown(
                f"<div class='{slug}-bubble-title'>{cfg.title}</div>"
                f"<div class='{slug}-bubble-sub'>{cfg.subtitle}</div>",
                unsafe_allow_html=True,
            )

        with st.container(key=f"{slug}_bubble_messages"):
            parts = [f"<div class='{slug}-bubble-messages-inner'>"]
            for msg in st.session_state.bubble_history:
                css_class = f"{slug}-bubble-user" if msg["role"] == "user" else f"{slug}-bubble-bot"
                parts.append(f"<div class='{css_class}'>{msg['content']}</div>")
            if st.session_state.bubble_thinking:
                parts.append(f"<div class='{slug}-bubble-typing'>Thinking...</div>")
            parts.append("</div>")
            st.markdown("".join(parts), unsafe_allow_html=True)

        with st.container(key=f"{slug}_bubble_inputrow"):
            q_col, btn_col = st.columns([5, 1])
            with q_col:
                question = st.text_input(
                    "", placeholder=cfg.placeholder,
                    label_visibility="collapsed",
                    key=f"bubble_input_{st.session_state.bubble_input_counter}",
                    disabled=st.session_state.bubble_thinking,
                )
            with btn_col:
                ask = st.button(
                    "Ask", use_container_width=True, key=f"{slug}_bubble_ask_btn",
                    disabled=st.session_state.bubble_thinking,
                )

            if ask and question and not st.session_state.bubble_thinking:
                st.session_state.bubble_history.append({"role": "user", "content": question})
                st.session_state.bubble_thinking = True
                st.session_state.bubble_input_counter += 1
                st.rerun()

    if st.session_state.bubble_thinking:
        last_question = st.session_state.bubble_history[-1]["content"]
        try:
            llm = _get_llm(cfg.model)
            sys_prompt = None
            if cfg.system_prompt_fn:
                try:
                    sys_prompt = cfg.system_prompt_fn()
                except Exception:
                    sys_prompt = None
            if not sys_prompt:
                sys_prompt = cfg.system_prompt
                if cfg.pre_message:
                    try:
                        extra = cfg.pre_message()
                        if extra:
                            sys_prompt = sys_prompt + "\n\n" + extra
                    except Exception:
                        pass
            messages = [SystemMessage(content=sys_prompt)]
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
