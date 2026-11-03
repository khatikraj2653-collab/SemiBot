"""
Interactive causal map: an SVG/JS widget that shows the 18 factors feeding the
UP probability and lets the user run "what if?" scenarios in the browser.

The probability formula and weights mirror graph/nodes.py (FACTOR_WEIGHTS and
calculate_probability); nothing here changes the stored analysis.
"""
import json
import os

import streamlit.components.v1 as components

FACTOR_KEYS = [
    "cpi", "ppi", "fed_rate", "usd_index",
    "pe_ratio", "market_cap", "earnings_guidance", "insider_selling",
    "sector_rally", "technical_signal", "analyst_ratings", "sell_the_news",
    "geopolitics", "supply_chain", "news_sentiment", "capital_rotation",
    "competitor_contagion", "beta",
]

_TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "causal_map.html")


def render_causal_map(ticker, scores, notes=None, height=760):
    """Render the interactive map for one analysis result."""
    with open(_TEMPLATE_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    clean_scores = {}
    for k in FACTOR_KEYS:
        try:
            clean_scores[k] = int((scores or {}).get(k, 0))
        except (TypeError, ValueError):
            clean_scores[k] = 0
    clean_notes = {k: str(v)[:900] for k, v in (notes or {}).items() if v}

    payload = json.dumps({"ticker": str(ticker), "scores": clean_scores, "notes": clean_notes})
    payload = payload.replace("</", "<\\/")  # keep the JSON from closing the <script> tag
    components.html(html.replace("__CM_DATA__", payload), height=height, scrolling=False)
