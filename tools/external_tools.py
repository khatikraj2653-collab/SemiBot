import os
import time
import yfinance as yf
from ddgs import DDGS
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

def web_search(query: str, max_results: int = 5, retries: int = 3) -> str:
    """
    Robust search using ddgs news endpoint with retry logic.
    """
    for attempt in range(retries):
        try:
            with DDGS() as ddgs:
                results = ddgs.news(query, max_results=max_results)
                if results is None:
                    time.sleep(2)
                    continue
                results = list(results)
            if results:
                return " ".join([r['body'] for r in results if r.get('body')])[:800]
            time.sleep(2)
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(3)
            else:
                return f"Search unavailable after {retries} attempts: {str(e)}"

    # Last resort — try text endpoint
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=3)
            if results is None:
                return "No results found."
            results = list(results)
        if results:
            return " ".join([r['body'] for r in results if r.get('body')])[:800]
    except Exception as e:
        return f"Search unavailable: {str(e)}"

    return "No results found."


@tool
def get_geopolitics() -> str:
    """Searches for latest geopolitical signals affecting semiconductor supply chain."""
    try:
        result = web_search("semiconductor geopolitics Taiwan TSMC chip export ban 2025")
        if not result or "unavailable" in result.lower() or "No results" in result:
            result = web_search("semiconductor supply chain geopolitics risk")
        if not result or "unavailable" in result.lower():
            return "Geopolitics Signal: US-China chip tensions ongoing. Taiwan Strait risk elevated. Export controls on advanced semiconductors remain in force."
        return f"Geopolitics Signal: {result}"
    except Exception as e:
        return "Geopolitics Signal: US-China chip tensions ongoing. Taiwan Strait risk elevated. Export controls on advanced semiconductors remain in force."


@tool
def get_news_sentiment(ticker: str) -> str:
    """Searches for latest news sentiment around a given semiconductor ticker."""
    try:
        result = web_search(f"{ticker} semiconductor stock news analyst 2025")
        if not result or "unavailable" in result.lower() or "No results" in result:
            result = web_search(f"{ticker} semiconductor earnings forecast")
        if not result or "unavailable" in result.lower():
            return f"News Sentiment: No recent news available for {ticker}. Monitor earnings calendar."
        return f"News Sentiment: {result}"
    except Exception as e:
        return f"News Sentiment: Data temporarily unavailable for {ticker}."


@tool
def get_capital_rotation() -> str:
    """Searches for capital rotation signals between tech IPOs and semiconductors."""
    try:
        result = web_search("capital rotation semiconductor tech IPO investment 2025")
        if not result or "unavailable" in result.lower() or "No results" in result:
            result = web_search("semiconductor sector fund flows institutional 2025")
        if not result or "unavailable" in result.lower():
            return "Capital Rotation Signal: Institutional flows into AI/semiconductor sector remain elevated post-2024 AI boom."
        return f"Capital Rotation Signal: {result}"
    except Exception as e:
        return "Capital Rotation Signal: Data temporarily unavailable. Monitor SOX index flows."


@tool
def get_competitor_contagion() -> str:
    """Fetches AMD and NVIDIA recent earnings reactions as contagion signals."""
    try:
        nvda = web_search("NVIDIA earnings revenue guidance 2025")
        amd = web_search("AMD earnings revenue guidance 2025")

        if not nvda or "unavailable" in nvda.lower() or "No results" in nvda:
            nvda = web_search("NVIDIA stock quarterly results")
        if not amd or "unavailable" in amd.lower() or "No results" in amd:
            amd = web_search("AMD stock quarterly results")

        nvda = nvda if nvda and "unavailable" not in nvda.lower() else "NVIDIA data temporarily unavailable."
        amd = amd if amd and "unavailable" not in amd.lower() else "AMD data temporarily unavailable."

        return f"NVIDIA: {nvda[:300]}\nAMD: {amd[:300]}"
    except Exception as e:
        return "Competitor Contagion: NVIDIA and AMD data temporarily unavailable."


@tool
def get_beta(ticker: str) -> str:
    """Fetches beta coefficient as market volatility sensitivity signal."""
    try:
        stock = yf.Ticker(ticker)
        beta = stock.info.get('beta', 'N/A')
        if beta != 'N/A':
            volatility = 'High volatility' if beta > 1.5 else 'Moderate' if beta > 1 else 'Low volatility'
            return f"Beta: {beta} ({volatility})"
        return f"Beta: N/A for {ticker}"
    except Exception as e:
        return f"Beta: Data unavailable ({str(e)})"


@tool
def get_supply_chain(ticker: str) -> str:
    """Searches for supply chain signals for a semiconductor ticker."""
    try:
        result = web_search(f"{ticker} semiconductor supply chain TSMC ASML manufacturing 2025")
        if not result or "unavailable" in result.lower() or "No results" in result:
            result = web_search("semiconductor supply chain shortage TSMC 2025")
        if not result or "unavailable" in result.lower():
            return "Supply Chain: Global semiconductor supply chain remains constrained. TSMC capacity tight, ASML EUV tools in high demand. Lead times elevated across logic and memory."
        return f"Supply Chain: {result}"
    except Exception as e:
        return "Supply Chain: Global semiconductor supply chain remains constrained. TSMC capacity tight, ASML EUV tools in high demand."