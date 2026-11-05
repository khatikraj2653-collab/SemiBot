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
        # Need at least 200 trading days for a meaningful 200-day MA
        if hist is None or hist.empty or len(hist) < 50:
            return f"Technical Signal: Not enough price history for {ticker} ({0 if hist is None else len(hist)} days)"
        closes = hist['Close'].dropna()
        if len(closes) < 50:
            return f"Technical Signal: Not enough price history for {ticker}"
        ma50_series = closes.rolling(50).mean().dropna()
        if ma50_series.empty:
            return f"Technical Signal: Not enough price history for {ticker}"
        ma50 = float(ma50_series.iloc[-1])
        # 200-day MA may be unavailable for younger listings — degrade gracefully
        if len(closes) >= 200:
            ma200_series = closes.rolling(200).mean().dropna()
            ma200 = float(ma200_series.iloc[-1])
            signal = "Golden Cross (Bullish)" if ma50 > ma200 else "Death Cross (Bearish)"
            return f"MA50: {round(ma50,2)}, MA200: {round(ma200,2)}, Signal: {signal}"
        # Fallback: compare current price vs 50-day MA
        last_price = float(closes.iloc[-1])
        signal = "Above 50-day MA (Bullish)" if last_price > ma50 else "Below 50-day MA (Bearish)"
        return f"MA50: {round(ma50,2)}, Price: {round(last_price,2)}, Signal: {signal} (200-day MA unavailable)"
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
