import os
import yfinance as yf
from langchain_core.tools import tool
from dotenv import load_dotenv
from tools.cache_utils import cached_tool, TTL_SLOW, TTL_FAST

load_dotenv()

def web_search(query: str, max_results: int = 3) -> str:
    """Web search using ddgs news endpoint."""
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.news(query, max_results=max_results))
        if results:
            return " ".join([r['body'] for r in results])[:800]
        return "No results found."
    except Exception as e:
        return f"Search unavailable: {str(e)}"

@tool
@cached_tool(TTL_SLOW)
def get_sector_rally() -> str:
    """Fetches 1-month SOXX ETF performance as semiconductor sector momentum signal."""
    try:
        soxx = yf.Ticker("SOXX")
        hist = soxx.history(period="1mo")
        change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
        return f"SOXX 1-month change: {round(change, 2)}% ({'Bullish' if change > 0 else 'Bearish'})"
    except Exception as e:
        return f"Sector Rally: Data unavailable ({str(e)})"

@tool
@cached_tool(TTL_SLOW)
def get_technical_signal(ticker: str) -> str:
    """Calculates 50-day and 200-day moving averages to identify golden or death cross."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        ma50 = hist['Close'].rolling(50).mean().iloc[-1]
        ma200 = hist['Close'].rolling(200).mean().iloc[-1]
        signal = "Golden Cross (Bullish)" if ma50 > ma200 else "Death Cross (Bearish)"
        return f"MA50: {round(ma50,2)}, MA200: {round(ma200,2)}, Signal: {signal}"
    except Exception as e:
        return f"Technical Signal: Data unavailable ({str(e)})"

@tool
@cached_tool(TTL_SLOW)
def get_analyst_ratings(ticker: str) -> str:
    """Fetches analyst buy/hold/sell recommendations for a given ticker."""
    try:
        stock = yf.Ticker(ticker)
        rating = stock.info.get('recommendationMean', 'N/A')
        key = stock.info.get('recommendationKey', 'N/A')
        return f"Analyst Rating: {key} (mean score: {rating}/5)"
    except Exception as e:
        return f"Analyst Ratings: Data unavailable ({str(e)})"

@tool
@cached_tool(TTL_FAST)
def get_sell_the_news(ticker: str) -> str:
    """Searches for sell-the-news risk signals around upcoming earnings."""
    try:
        result = web_search(f"{ticker} stock price reaction after earnings report semiconductor company")
        return f"Sell-the-News Signal: {result}"
    except Exception as e:
        return f"Sell-the-News: Data unavailable ({str(e)})"
