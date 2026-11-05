import os
import yfinance as yf
import requests
from langchain_core.tools import tool
from dotenv import load_dotenv
from tools.cache_utils import cached_tool, TTL_SLOW

load_dotenv()

@tool
@cached_tool(TTL_SLOW)
def get_pe_ratio(ticker: str) -> str:
    """Fetches trailing P/E ratio for a given semiconductor ticker."""
    try:
        stock = yf.Ticker(ticker)
        pe = stock.info.get('trailingPE', 'N/A')
        return f"P/E Ratio: {pe}"
    except Exception as e:
        return f"P/E Ratio: Data unavailable ({str(e)})"

@tool
@cached_tool(TTL_SLOW)
def get_market_cap(ticker: str) -> str:
    """Fetches current market capitalization for a given ticker."""
    try:
        stock = yf.Ticker(ticker)
        mc = stock.info.get('marketCap', None)
        if isinstance(mc, (int, float)) and mc > 0:
            return f"Market Cap: ${mc:,.0f}"
        return f"Market Cap: N/A (not reported for {ticker})"
    except Exception as e:
        return f"Market Cap: Data unavailable ({str(e)})"

@tool
@cached_tool(TTL_SLOW)
def get_earnings_guidance(ticker: str) -> str:
    """Fetches next earnings date and forward EPS estimate for a given ticker."""
    try:
        stock = yf.Ticker(ticker)
        eps = stock.info.get('forwardEps', 'N/A')
        growth = stock.info.get('earningsGrowth', 'N/A')
        return f"Forward EPS: {eps}, Earnings Growth: {growth}"
    except Exception as e:
        return f"Earnings Guidance: Data unavailable ({str(e)})"

@tool
@cached_tool(TTL_SLOW)
def get_insider_selling(ticker: str) -> str:
    """Fetches recent insider transaction data from Yahoo Finance."""
    try:
        stock = yf.Ticker(ticker)
        insider = stock.insider_transactions
        if insider is not None and not insider.empty:
            recent = insider.head(3)
            lines = []
            for _, row in recent.iterrows():
                name = row.get('Insider', 'Unknown')
                shares = row.get('Shares', 'N/A')
                value = row.get('Value', 'N/A')
                text = row.get('Text', '')
                # Format value as dollar amount if numeric and not NaN
                if isinstance(value, (int, float)) and not (isinstance(value, float) and value != value):
                    value = f"${value:,.0f}"
                else:
                    value = "Not disclosed"
                lines.append(f"{name}: {text} | Shares: {shares} | Value: {value}")
            return "Recent Insider Transactions:\n" + "\n".join(lines)
        return "Insider Selling: No recent transactions found"
    except Exception as e:
        return f"Insider Selling: Data unavailable ({str(e)})"
