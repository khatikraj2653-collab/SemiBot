"""
Thin wrapper around the shared chat_bubble_core. Configures theme and
dynamic system prompt for SemiBot (includes live prices for common tickers
and optional per-ticker analysis context).
"""
import streamlit as st
import yfinance as yf

from chat_bubble_core import BubbleConfig, BubbleTheme, render_bubble

LIVE_PRICE_TICKERS = ["MU", "NVDA", "AMD", "INTC", "TSM", "ASML", "QCOM", "AVGO", "AMAT", "LRCX", "ARM", "TXN", "ADI", "MCHP", "ON"]


@st.cache_data(ttl=900)
def get_live_prices_text():
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
    return (
        f"\n\nLIVE PRICES (last close, refreshed periodically): {prices}\n"
        "You CAN and SHOULD use these to answer 'what's the current price of X' "
        "for any ticker listed above."
    )


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


_THEME = BubbleTheme(
    slug="semibot",
    accent="#5B9BFF",
    accent_hover="#7FB0FF",
    text_primary="#EDF0F5",
    text_secondary="#9AA6B8",
    bg_panel="#1E2633",
    bg_input="#15191D",
    bubble_icon_color="#0C1015",
    hair="rgba(146,163,192,.15)",
)


def render_chat_bubble(get_system_prompt=None):
    """
    get_system_prompt: optional callable() -> str, builds richer context
    (e.g. current ticker analysis) based on session state at ask-time.
    Falls back to the generic SemiBot identity prompt if not provided or
    if no analysis context is currently available.
    """
    def _prompt_fn():
        if get_system_prompt:
            try:
                p = get_system_prompt()
                if p:
                    return p
            except Exception:
                pass
        return build_generic_prompt()

    cfg = BubbleConfig(
        theme=_THEME,
        title="Ask SemiBot",
        subtitle="Semiconductor market Q&amp;A - won't answer off-topic questions",
        placeholder="Ask about semiconductor stocks...",
        system_prompt=GENERIC_SYSTEM_PROMPT_TEMPLATE,  # fallback, overridden by fn
        system_prompt_fn=_prompt_fn,
    )
    render_bubble(cfg)
